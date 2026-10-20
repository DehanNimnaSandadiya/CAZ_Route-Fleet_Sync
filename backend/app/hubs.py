"""Micro-hub cargo-bike handshake: plan + lifecycle."""
from __future__ import annotations
import math
import uuid
from dataclasses import dataclass, field
from typing import Optional

from .compliance import Vehicle, daily_charge
from .config import DRIVER_RATE_GBP_PER_H, HANDSHAKE_FEE_GBP, RIDER_RATE_GBP_PER_H
from .engine import CARGO_BIKE, VAN, Graph, route

STATES = ["CREATED", "VAN_ARRIVED", "HANDED_OVER", "OUT_FOR_DELIVERY", "DELIVERED"]
FAILURE_STATES = {"FAILED", "CANCELLED"}


@dataclass
class Hub:
    id: str
    name: str
    node_id: str
    capacity_parcels: int
    bike_capacity_parcels: int = 12     # per cargo-bike trip (assumption; set per operator)
    reserved: int = 0

    @property
    def free(self) -> int:
        return self.capacity_parcels - self.reserved


@dataclass
class Handshake:
    id: str
    hub_id: str
    van_reg: str
    dest_node: str
    parcels: int
    state: str = "CREATED"
    fee_gbp: float = 0.0
    history: list[str] = field(default_factory=lambda: ["CREATED"])


class HubService:
    def __init__(self, graph: Graph) -> None:
        self.g = graph
        self.hubs: dict[str, Hub] = {}
        self.handshakes: dict[str, Handshake] = {}

    def add_hub(self, hub: Hub) -> None:
        if hub.node_id not in self.g.nodes:
            raise ValueError("hub node not in graph")
        self.hubs[hub.id] = hub

    def plan(self, origin: str, dest: str, hub_id: str, vehicle: Vehicle, parcels: int) -> dict:
        hub = self.hubs.get(hub_id)
        if hub is None:
            raise KeyError("unknown hub")
        charge = daily_charge(vehicle)
        direct = route(self.g, origin, dest, VAN, charge)
        leg1 = route(self.g, origin, hub.node_id, VAN, charge)
        leg2 = route(self.g, hub.node_id, dest, CARGO_BIKE, 0.0)
        if not (leg1.found and leg2.found):
            return {"feasible": False, "reason": "no feasible van->hub or bike->destination leg"}
        if hub.free < parcels:
            return {"feasible": False, "reason": f"hub has {hub.free} free slots, need {parcels}"}
        direct_cost = None
        if direct.found:
            direct_cost = direct.duration_s / 3600 * DRIVER_RATE_GBP_PER_H + direct.caz_charge_gbp
        trips = math.ceil(parcels / hub.bike_capacity_parcels)
        bike_cost = 2 * leg2.duration_s / 3600 * RIDER_RATE_GBP_PER_H * trips  # round trips
        fee = HANDSHAKE_FEE_GBP * parcels
        van_cost = leg1.duration_s / 3600 * DRIVER_RATE_GBP_PER_H + leg1.caz_charge_gbp
        handshake_cost = van_cost + bike_cost + fee
        return {
            "feasible": True,
            "direct": direct.as_dict(self.g) if direct.found else None,
            "direct_cost_gbp": None if direct_cost is None else round(direct_cost, 2),
            "van_leg": leg1.as_dict(self.g), "bike_leg": leg2.as_dict(self.g),
            "bike_trips": trips, "platform_fee_gbp": round(fee, 2),
            "handshake_cost_gbp": round(handshake_cost, 2),
            "recommend_handshake": direct_cost is None or handshake_cost < direct_cost,
            "assumptions": "one-way van time; bike cost = round trips x rider rate; rates in config.py",
        }

    def create(self, hub_id: str, van_reg: str, dest_node: str, parcels: int) -> Handshake:
        hub = self.hubs.get(hub_id)
        if hub is None:
            raise KeyError("unknown hub")
        if parcels < 1:
            raise ValueError("parcels must be >= 1")
        if hub.free < parcels:
            raise ValueError("insufficient hub capacity")
        hub.reserved += parcels
        h = Handshake(uuid.uuid4().hex[:12], hub_id, van_reg.upper(), dest_node, parcels,
                      fee_gbp=round(HANDSHAKE_FEE_GBP * parcels, 2))
        self.handshakes[h.id] = h
        return h

    def advance(self, hs_id: str, new_state: str) -> Handshake:
        h = self.handshakes[hs_id]
        hub = self.hubs[h.hub_id]
        if h.state in FAILURE_STATES or h.state == "DELIVERED":
            raise ValueError(f"handshake already {h.state}")
        if new_state in FAILURE_STATES:
            hub.reserved -= h.parcels
            h.state = new_state
        else:
            if new_state not in STATES or STATES.index(new_state) != STATES.index(h.state) + 1:
                raise ValueError(f"invalid transition {h.state} -> {new_state}")
            h.state = new_state
            if new_state == "DELIVERED":
                hub.reserved -= h.parcels
        h.history.append(h.state)
        return h
