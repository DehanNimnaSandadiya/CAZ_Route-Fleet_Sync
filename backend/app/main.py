"""CAZ-Route & Fleet Sync (Bristol) - API (prototype). Run: uvicorn app.main:app --reload"""
from __future__ import annotations
from datetime import date
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .compliance import (ComplianceLedger, Vehicle, daily_charge, is_compliant, payment_window,
                         pcn_exposure, pcn_risk_score)
from .engine import CARGO_BIKE, VAN, route
from .hubs import Hub, HubService
from .marketplace import DropNode, Marketplace
from .seed import build_demo_graph

app = FastAPI(title="CAZ-Route & Fleet Sync (Bristol)", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["*"], allow_headers=["*"])

GRAPH = build_demo_graph()
LEDGER = ComplianceLedger()
HUBS = HubService(GRAPH)
MARKET = Marketplace()
HUBS.add_hub(Hub("hub-marsh", "St Philip's Marsh depot (candidate)", "MARSH", capacity_parcels=200))
MARKET.add_node(DropNode("drop-clifton-1", "Clifton Village corner shop locker", "Example Deli Ltd",
                         "CLIFTONV", slots_per_day=20, price_per_slot_gbp=0.80))


class VehicleIn(BaseModel):
    reg: str = Field(min_length=2, max_length=10)
    vehicle_class: Literal["car", "taxi", "van", "minibus", "hgv", "bus", "coach", "cargo_bike"]
    fuel: Literal["diesel", "petrol", "electric", "hydrogen", "hybrid_petrol", "hybrid_diesel", "pedal"]
    euro_standard: Optional[int] = Field(default=None, ge=1, le=7)
    exempt: bool = False

    def to_domain(self) -> Vehicle:
        return Vehicle(self.reg.upper(), self.vehicle_class, self.fuel, self.euro_standard, self.exempt)


class RouteIn(BaseModel):
    origin: str
    destination: str
    vehicle: VehicleIn
    travel_day: date
    today: Optional[date] = None
    payment_confirmed: bool = False


@app.get("/health")
def health():
    return {"status": "ok", "data": "illustrative seed graph - replace with OSM/terrain import"}


@app.get("/nodes")
def nodes():
    return [n.__dict__ for n in GRAPH.nodes.values()]


@app.post("/compliance/check")
def compliance_check(v: VehicleIn):
    d = v.to_domain()
    return {"compliant": is_compliant(d), "daily_charge_gbp": daily_charge(d)}


@app.post("/route")
def plan_route(r: RouteIn):
    today = r.today or date.today()
    v = r.vehicle.to_domain()
    mode = CARGO_BIKE if v.vehicle_class == "cargo_bike" else VAN
    charge = daily_charge(v)
    best = route(GRAPH, r.origin, r.destination, mode, charge)
    if not best.found:
        raise HTTPException(422, best.reason)
    naive = route(GRAPH, r.origin, r.destination, mode, charge, avoid_caz_weight=False)
    entry = None
    if best.enters_caz:
        entry = LEDGER.record_entry(v, r.travel_day)
    risk = pcn_risk_score(v, best.enters_caz, r.travel_day, LEDGER, today, r.payment_confirmed)
    lo, hi = payment_window(r.travel_day)
    return {
        "recommended": best.as_dict(GRAPH),
        "fastest_ignoring_caz": naive.as_dict(GRAPH),
        "charge_avoided_gbp": round(naive.caz_charge_gbp - best.caz_charge_gbp, 2),
        "pcn_risk": risk,
        "payment_window": {"opens": lo.isoformat(), "closes": hi.isoformat()},
        "ledger_entry_created": entry is not None,
    }


class PayIn(BaseModel):
    reg: str
    travel_day: date
    paid_on: date


@app.get("/ledger/{reg}")
def ledger(reg: str, today: Optional[date] = None):
    today = today or date.today()
    es = LEDGER.list(reg)
    return {
        "entries": [{"reg": e.reg, "day": e.day.isoformat(), "charge_gbp": e.charge,
                     "paid_on": e.paid_on.isoformat() if e.paid_on else None,
                     "deadline": LEDGER.deadline(e).isoformat(), "status": LEDGER.status(e, today)}
                    for e in es],
        "exposure": pcn_exposure(es, today),
    }


@app.post("/ledger/pay")
def ledger_pay(p: PayIn):
    try:
        e = LEDGER.mark_paid(p.reg, p.travel_day, p.paid_on)
    except KeyError as ex:
        raise HTTPException(404, str(ex))
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"reg": e.reg, "day": e.day.isoformat(), "paid_on": e.paid_on.isoformat()}  # type: ignore[union-attr]


class PlanIn(BaseModel):
    origin: str
    destination: str
    hub_id: str
    vehicle: VehicleIn
    parcels: int = Field(ge=1, le=500)


@app.post("/handshake/plan")
def handshake_plan(p: PlanIn):
    try:
        return HUBS.plan(p.origin, p.destination, p.hub_id, p.vehicle.to_domain(), p.parcels)
    except KeyError as ex:
        raise HTTPException(404, str(ex))


class HsCreate(BaseModel):
    hub_id: str
    van_reg: str
    destination: str
    parcels: int = Field(ge=1, le=500)


@app.post("/handshake")
def handshake_create(b: HsCreate):
    try:
        return HUBS.create(b.hub_id, b.van_reg, b.destination, b.parcels).__dict__
    except KeyError as ex:
        raise HTTPException(404, str(ex))
    except ValueError as ex:
        raise HTTPException(422, str(ex))


class HsAdvance(BaseModel):
    state: str


@app.post("/handshake/{hs_id}/advance")
def handshake_advance(hs_id: str, b: HsAdvance):
    try:
        return HUBS.advance(hs_id, b.state).__dict__
    except KeyError:
        raise HTTPException(404, "unknown handshake")
    except ValueError as ex:
        raise HTTPException(422, str(ex))


class BookIn(BaseModel):
    business: str
    day: date
    slots: int = Field(ge=1, le=100)


@app.get("/marketplace/nodes")
def market_nodes(day: Optional[date] = None):
    day = day or date.today()
    return [{"id": n.id, "name": n.name, "host": n.host_business, "free_slots": MARKET.free_slots(n.id, day),
             "price_per_slot_gbp": n.price_per_slot_gbp} for n in MARKET.nodes.values()]


@app.post("/marketplace/nodes/{node_id}/book")
def market_book(node_id: str, b: BookIn):
    if node_id not in MARKET.nodes:
        raise HTTPException(404, "unknown drop node")
    try:
        bk = MARKET.book(node_id, b.business, b.day, b.slots)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"booking": bk.__dict__ | {"day": bk.day.isoformat()}, "quote": MARKET.quote(node_id, b.slots)}
