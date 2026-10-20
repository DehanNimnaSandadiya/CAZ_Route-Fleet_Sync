"""Topography- and CAZ-aware routing engine (prototype).

State-space Dijkstra over (node, caz_charged). The daily CAZ charge is applied ONCE, the first time a
chargeable vehicle touches a CAZ node, so routes are not penalised repeatedly for the same day's charge.
Production swaps this graph for a PostGIS/pgRouting (or Valhalla/OSRM-custom) network built from OSM +
a terrain model; the cost function below carries over unchanged.
"""
from __future__ import annotations
import heapq
import math
from dataclasses import dataclass, field
from typing import Optional

from .config import VALUE_OF_TIME_S_PER_GBP


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


@dataclass(frozen=True)
class Node:
    id: str
    name: str
    lat: float
    lon: float
    elev_m: float
    in_caz: bool = False


@dataclass(frozen=True)
class ModeProfile:
    name: str                 # van | cargo_bike
    base_speed_kmh: float
    max_grade_pct: float      # edges steeper than this (in direction of travel, uphill) are impassable
    uphill_slowdown: float    # fractional speed loss per 1% uphill grade
    downhill_gain_cap: float  # max speed multiplier on descents
    min_speed_factor: float = 0.3
    uses_roads_only: bool = False   # True => cannot use bike-only edges


VAN = ModeProfile("van", 24.0, 25.0, 0.015, 1.1, 0.5, True)
CARGO_BIKE = ModeProfile("cargo_bike", 15.0, 12.0, 0.06, 1.25, 0.3, False)
PROFILES = {"van": VAN, "cargo_bike": CARGO_BIKE}


@dataclass
class Edge:
    to: str
    length_m: float
    road_type: str = "road"   # road | bike_only | congested_road
    congestion_factor: float = 1.0   # >=1 multiplies travel time (e.g. peak-hour A38 / M32 approach)


class Graph:
    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.adj: dict[str, list[Edge]] = {}

    def add_node(self, n: Node) -> None:
        self.nodes[n.id] = n
        self.adj.setdefault(n.id, [])

    def add_edge(self, a: str, b: str, road_type: str = "road", congestion: float = 1.0,
                 length_m: Optional[float] = None) -> None:
        na, nb = self.nodes[a], self.nodes[b]
        d = length_m if length_m is not None else haversine_m(na.lat, na.lon, nb.lat, nb.lon) * 1.25  # street-winding factor
        self.adj[a].append(Edge(b, d, road_type, congestion))
        self.adj[b].append(Edge(a, d, road_type, congestion))

    def grade_pct(self, a: str, b: str, length_m: float) -> float:
        return (self.nodes[b].elev_m - self.nodes[a].elev_m) / max(length_m, 1.0) * 100.0


@dataclass
class RouteResult:
    found: bool
    path: list[str] = field(default_factory=list)
    distance_m: float = 0.0
    duration_s: float = 0.0
    ascent_m: float = 0.0
    max_grade_pct: float = 0.0
    enters_caz: bool = False
    caz_charge_gbp: float = 0.0
    reason: str = ""

    def as_dict(self, g: Graph) -> dict:
        return {
            "found": self.found, "reason": self.reason,
            "path": [{"id": i, "name": g.nodes[i].name, "lat": g.nodes[i].lat, "lon": g.nodes[i].lon,
                      "elev_m": g.nodes[i].elev_m, "in_caz": g.nodes[i].in_caz} for i in self.path],
            "distance_m": round(self.distance_m), "duration_min": round(self.duration_s / 60, 1),
            "ascent_m": round(self.ascent_m, 1), "max_grade_pct": round(self.max_grade_pct, 1),
            "enters_caz": self.enters_caz, "caz_charge_gbp": self.caz_charge_gbp,
        }


def edge_time_s(g: Graph, a: str, e: Edge, p: ModeProfile) -> Optional[float]:
    """Travel time in seconds, or None if the edge is impassable for this mode."""
    if e.road_type == "bike_only" and p.uses_roads_only:
        return None
    grade = g.grade_pct(a, e.to, e.length_m)
    if grade > p.max_grade_pct:
        return None
    if grade >= 0:
        factor = max(p.min_speed_factor, 1.0 - p.uphill_slowdown * grade)
    else:
        factor = min(p.downhill_gain_cap, 1.0 + p.uphill_slowdown * 0.5 * abs(grade))
    speed_ms = p.base_speed_kmh / 3.6 * factor
    t = e.length_m / speed_ms
    if not (p.name == "cargo_bike"):          # bikes filter past congestion
        t *= e.congestion_factor
    return t


def route(g: Graph, src: str, dst: str, profile: ModeProfile, caz_charge_gbp: float = 0.0,
          avoid_caz_weight: bool = True) -> RouteResult:
    """Least-cost route. `caz_charge_gbp` > 0 means the vehicle is chargeable inside the CAZ.
    If avoid_caz_weight is False the charge is still *reported* but does not influence the choice
    (used to show the naive fastest route for comparison)."""
    if src not in g.nodes or dst not in g.nodes:
        return RouteResult(False, reason="unknown node")
    penalty_s = caz_charge_gbp * VALUE_OF_TIME_S_PER_GBP if avoid_caz_weight else 0.0
    start_charged = g.nodes[src].in_caz and caz_charge_gbp > 0
    start_cost = penalty_s if start_charged else 0.0
    best: dict[tuple[str, bool], float] = {(src, start_charged): start_cost}
    prev: dict[tuple[str, bool], Optional[tuple[str, bool]]] = {(src, start_charged): None}
    heap = [(start_cost, src, start_charged)]
    goal: Optional[tuple[str, bool]] = None
    while heap:
        cost, u, charged = heapq.heappop(heap)
        if cost > best.get((u, charged), math.inf):
            continue
        if u == dst:
            goal = (u, charged)
            break
        for e in g.adj[u]:
            t = edge_time_s(g, u, e, profile)
            if t is None:
                continue
            ncharged = charged or (g.nodes[e.to].in_caz and caz_charge_gbp > 0)
            add = t + (penalty_s if (ncharged and not charged) else 0.0)
            nc = cost + add
            key = (e.to, ncharged)
            if nc < best.get(key, math.inf):
                best[key] = nc
                prev[key] = (u, charged)
                heapq.heappush(heap, (nc, e.to, ncharged))
    if goal is None:
        return RouteResult(False, reason="no feasible route for this vehicle profile")
    states = []
    cur: Optional[tuple[str, bool]] = goal
    while cur is not None:
        states.append(cur)
        cur = prev[cur]
    states.reverse()
    path = [s[0] for s in states]
    return _summarise(g, path, profile, caz_charge_gbp)


def _summarise(g: Graph, path: list[str], p: ModeProfile, caz_charge_gbp: float) -> RouteResult:
    dist = dur = ascent = maxg = 0.0
    for a, b in zip(path, path[1:]):
        e = min((x for x in g.adj[a] if x.to == b and edge_time_s(g, a, x, p) is not None),
                key=lambda x: edge_time_s(g, a, x, p))
        dist += e.length_m
        dur += edge_time_s(g, a, e, p)  # type: ignore[operator]
        d_el = g.nodes[b].elev_m - g.nodes[a].elev_m
        ascent += max(0.0, d_el)
        maxg = max(maxg, g.grade_pct(a, b, e.length_m))
    enters = any(g.nodes[n].in_caz for n in path)
    return RouteResult(True, path, dist, dur, ascent, maxg, enters,
                       caz_charge_gbp if enters else 0.0)
