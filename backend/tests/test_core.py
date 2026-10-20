from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.compliance import (ComplianceLedger, Vehicle, daily_charge, is_compliant, payment_window,
                            pcn_exposure, pcn_risk_score)
from app.engine import CARGO_BIKE, VAN, route
from app.hubs import Hub, HubService
from app.main import app
from app.marketplace import DropNode, Marketplace
from app.seed import build_demo_graph

OLD_DIESEL = Vehicle("AB12CDE", "van", "diesel", 5)
NEW_DIESEL = Vehicle("XY21ZZZ", "van", "diesel", 6)
OLD_PETROL = Vehicle("P1", "car", "petrol", 3)
HGV = Vehicle("H1", "hgv", "diesel", 5)


def test_compliance_rules():
    assert is_compliant(OLD_DIESEL) is False and daily_charge(OLD_DIESEL) == 9.0
    assert is_compliant(NEW_DIESEL) is True and daily_charge(NEW_DIESEL) == 0.0
    assert is_compliant(OLD_PETROL) is False
    assert is_compliant(Vehicle("P2", "car", "petrol", 4)) is True
    assert daily_charge(HGV) == 100.0
    assert is_compliant(Vehicle("E1", "van", "electric")) is True
    assert is_compliant(Vehicle("U1", "van", "diesel")) is None
    assert daily_charge(Vehicle("U1", "van", "diesel")) == 9.0  # unknown => chargeable (safe side)


def test_payment_window_and_ledger():
    day = date(2026, 10, 1)
    assert payment_window(day) == (date(2026, 9, 25), date(2026, 10, 7))
    led = ComplianceLedger()
    e1 = led.record_entry(OLD_DIESEL, day)
    e2 = led.record_entry(OLD_DIESEL, day)
    assert e1 is e2 and len(led.list()) == 1          # once per day
    assert led.record_entry(NEW_DIESEL, day) is None
    assert led.status(e1, date(2026, 10, 7)) == "due"
    assert led.status(e1, date(2026, 10, 8)) == "overdue_pcn_likely"
    with pytest.raises(ValueError):
        led.mark_paid("AB12CDE", day, date(2026, 10, 8))
    led.mark_paid("ab12cde", day, date(2026, 10, 2))
    assert led.status(e1, date(2026, 12, 1)) == "paid"


def test_pcn_exposure_and_risk():
    day = date(2026, 9, 1)
    led = ComplianceLedger()
    led.record_entry(OLD_DIESEL, day)
    exp = pcn_exposure(led.list(), date(2026, 10, 7))
    assert exp == {"overdue_days": 1, "outstanding_charges_gbp": 9.0,
                   "pcn_if_paid_within_14_days_gbp": 60.0, "pcn_full_gbp": 120.0}
    r = pcn_risk_score(OLD_DIESEL, True, date(2026, 10, 1), led, date(2026, 10, 8))  # window closed
    assert r["level"] == "high" and r["score"] == 70
    assert pcn_risk_score(NEW_DIESEL, True, date(2026, 10, 7), led, date(2026, 10, 7))["score"] == 0
    assert pcn_risk_score(OLD_DIESEL, False, date(2026, 10, 7), ComplianceLedger(), date(2026, 10, 7))["score"] == 0
    paid = pcn_risk_score(OLD_DIESEL, True, date(2026, 10, 7), ComplianceLedger(), date(2026, 10, 7), True)
    assert paid["level"] == "low"


def test_routing_avoids_caz_when_cheaper():
    g = build_demo_graph()
    # Non-chargeable vehicle may use CAZ freely
    free = route(g, "OLDMKT", "CLIFTONV", VAN, 0.0)
    assert free.found
    # Chargeable van: charge reported only if the chosen route enters CAZ
    r = route(g, "OLDMKT", "CLIFTONV", VAN, 9.0)
    assert r.found and r.caz_charge_gbp == (9.0 if r.enters_caz else 0.0)
    # With a huge charge the route avoids the zone entirely (A38 -> Whiteladies -> Clifton exists)
    avoid = route(g, "OLDMKT", "CLIFTONV", VAN, 100000.0)
    assert avoid.found and not avoid.enters_caz and avoid.caz_charge_gbp == 0.0
    # Starting inside the zone is charged once, not per edge
    inside = route(g, "CENTRE", "QSQ", VAN, 9.0)
    assert inside.enters_caz and inside.caz_charge_gbp == 9.0


def test_topography_limits_bikes_and_blocks_van_on_bike_only():
    g = build_demo_graph()
    # Bike cannot use a >12% climb; vans cannot use bike-only edges
    steep = [(a, e) for a, es in g.adj.items() for e in es if g.grade_pct(a, e.to, e.length_m) > CARGO_BIKE.max_grade_pct]
    assert steep, "seed graph should contain climbs steeper than bike limit"
    van_bike_link = route(g, "TMEADS", "HOTWELLS", VAN, 0.0)
    assert van_bike_link.found and "HOTWELLS" in van_bike_link.path
    assert route(g, "TMEADS", "HOTWELLS", CARGO_BIKE, 0.0).found
    assert not route(g, "NOPE", "HOTWELLS", VAN, 0.0).found
    # Van takes the direct steep link; bike must detour via Park Street
    assert route(g, "HOTWELLS", "CLIFTONV", VAN, 0.0).path == ["HOTWELLS", "CLIFTONV"]
    bike = route(g, "HOTWELLS", "CLIFTONV", CARGO_BIKE, 0.0)
    assert bike.found and len(bike.path) > 2 and bike.max_grade_pct <= CARGO_BIKE.max_grade_pct


def test_handshake_plan_and_lifecycle():
    g = build_demo_graph()
    hs = HubService(g)
    hs.add_hub(Hub("h1", "Marsh", "MARSH", capacity_parcels=10, bike_capacity_parcels=5))
    plan = hs.plan("M32J", "CLIFTONV", "h1", OLD_DIESEL, 8)
    assert plan["feasible"] and plan["bike_trips"] == 2 and plan["platform_fee_gbp"] == pytest.approx(9.6)
    too_many = hs.plan("M32J", "CLIFTONV", "h1", OLD_DIESEL, 11)
    assert not too_many["feasible"]
    h = hs.create("h1", "ab12cde", "CLIFTONV", 8)
    assert hs.hubs["h1"].free == 2
    with pytest.raises(ValueError):
        hs.advance(h.id, "DELIVERED")                 # cannot skip states
    for s in ["VAN_ARRIVED", "HANDED_OVER", "OUT_FOR_DELIVERY", "DELIVERED"]:
        hs.advance(h.id, s)
    assert hs.hubs["h1"].free == 10                    # capacity released
    with pytest.raises(ValueError):
        hs.advance(h.id, "CANCELLED")


def test_marketplace():
    m = Marketplace()
    m.add_node(DropNode("d1", "Locker", "Deli", "CLIFTONV", 5, 1.0))
    day = date(2026, 10, 8)
    m.book("d1", "Plumbing Co", day, 3)
    with pytest.raises(ValueError):
        m.book("d1", "Sparks Ltd", day, 3)
    m.book("d1", "Sparks Ltd", day, 2)
    assert m.free_slots("d1", day) == 0
    assert m.quote("d1", 10) == {"gross_gbp": 10.0, "platform_fee_gbp": 1.0, "host_payout_gbp": 9.0}
    assert sum(m.pool_split("d1", day).values()) == pytest.approx(5.0)


def test_api_end_to_end():
    c = TestClient(app)
    assert c.get("/health").status_code == 200
    body = {"origin": "OLDMKT", "destination": "CLIFTONV", "travel_day": "2026-10-08", "today": "2026-10-07",
            "vehicle": {"reg": "ab12cde", "vehicle_class": "van", "fuel": "diesel", "euro_standard": 5}}
    r = c.post("/route", json=body)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["recommended"]["found"] and j["charge_avoided_gbp"] >= 0
    assert j["payment_window"] == {"opens": "2026-10-02", "closes": "2026-10-14"}
    assert c.post("/route", json={**body, "destination": "NOPE"}).status_code == 422
    assert c.post("/compliance/check", json=body["vehicle"]).json() == {"compliant": False, "daily_charge_gbp": 9.0}
    assert c.post("/route", json={**body, "vehicle": {**body["vehicle"], "fuel": "steam"}}).status_code == 422
    # force a ledger entry via a CAZ-touching route, then pay it
    r2 = c.post("/route", json={**body, "origin": "CENTRE", "destination": "QSQ"})
    assert r2.json()["ledger_entry_created"] is True
    assert c.post("/ledger/pay", json={"reg": "AB12CDE", "travel_day": "2026-10-08", "paid_on": "2026-10-09"}).status_code == 200
    led = c.get("/ledger/AB12CDE", params={"today": "2026-10-20"}).json()
    assert led["entries"][0]["status"] == "paid" and led["exposure"]["overdue_days"] == 0
    assert c.post("/ledger/pay", json={"reg": "NONE", "travel_day": "2026-10-08", "paid_on": "2026-10-09"}).status_code == 404
    plan = c.post("/handshake/plan", json={"origin": "M32J", "destination": "CLIFTONV", "hub_id": "hub-marsh",
                                           "vehicle": body["vehicle"], "parcels": 6})
    assert plan.status_code == 200 and plan.json()["feasible"]
    hs = c.post("/handshake", json={"hub_id": "hub-marsh", "van_reg": "ab12cde", "destination": "CLIFTONV", "parcels": 6}).json()
    assert c.post(f"/handshake/{hs['id']}/advance", json={"state": "VAN_ARRIVED"}).status_code == 200
    assert c.post(f"/handshake/{hs['id']}/advance", json={"state": "DELIVERED"}).status_code == 422
    nodes = c.get("/marketplace/nodes", params={"day": "2026-10-08"}).json()
    assert nodes[0]["free_slots"] == 20
    bk = c.post("/marketplace/nodes/drop-clifton-1/book", json={"business": "Sparks", "day": "2026-10-08", "slots": 4})
    assert bk.status_code == 200 and bk.json()["quote"]["gross_gbp"] == 3.2
