"""CAZ compliance checks, daily-charge ledger and PCN risk predictor."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from .config import RULES

LIGHT = {"car", "taxi", "van", "minibus"}
HEAVY = {"hgv", "bus", "coach"}
ZERO_EMISSION_FUELS = {"electric", "hydrogen"}


@dataclass
class Vehicle:
    reg: str
    vehicle_class: str          # car|taxi|van|minibus|hgv|bus|coach|cargo_bike
    fuel: str                   # diesel|petrol|electric|hydrogen|hybrid_petrol|hybrid_diesel|pedal
    euro_standard: Optional[int] = None
    exempt: bool = False        # council-granted exemption (verify on bristol.gov.uk)


def is_compliant(v: Vehicle) -> Optional[bool]:
    """True/False, or None when it cannot be determined (unknown Euro standard)."""
    if v.exempt or v.vehicle_class == "cargo_bike" or v.fuel in ZERO_EMISSION_FUELS or v.fuel == "pedal":
        return True
    if v.euro_standard is None:
        return None
    if v.fuel in ("diesel", "hybrid_diesel"):
        return v.euro_standard >= RULES.min_diesel_euro
    if v.fuel in ("petrol", "hybrid_petrol"):
        return v.euro_standard >= RULES.min_petrol_euro
    return None


def daily_charge(v: Vehicle) -> float:
    """Charge if the vehicle enters the zone. Unknown compliance is treated as chargeable (safe side)."""
    if is_compliant(v) is True:
        return 0.0
    if v.vehicle_class in HEAVY:
        return RULES.charge_heavy
    if v.vehicle_class in LIGHT:
        return RULES.charge_light
    return 0.0


def payment_window(travel_day: date) -> tuple[date, date]:
    """Inclusive window in which the charge for `travel_day` may be paid."""
    return (travel_day - timedelta(days=RULES.pay_window_days_before),
            travel_day + timedelta(days=RULES.pay_window_days_after))


@dataclass
class LedgerEntry:
    reg: str
    day: date
    charge: float
    paid_on: Optional[date] = None
    source: str = "route_plan"   # route_plan | manual | anpr_import


class ComplianceLedger:
    """One entry per vehicle per day (the daily charge applies once per day)."""

    def __init__(self) -> None:
        self._entries: dict[tuple[str, date], LedgerEntry] = {}

    def record_entry(self, v: Vehicle, day: date, source: str = "route_plan") -> Optional[LedgerEntry]:
        charge = daily_charge(v)
        if charge == 0.0:
            return None
        key = (v.reg.upper(), day)
        if key not in self._entries:
            self._entries[key] = LedgerEntry(v.reg.upper(), day, charge, source=source)
        return self._entries[key]

    def mark_paid(self, reg: str, day: date, paid_on: date) -> LedgerEntry:
        e = self._entries.get((reg.upper(), day))
        if e is None:
            raise KeyError("no ledger entry for that vehicle/day")
        lo, hi = payment_window(day)
        if not (lo <= paid_on <= hi):
            raise ValueError(f"payment date {paid_on} outside window {lo}..{hi}")
        e.paid_on = paid_on
        return e

    def status(self, e: LedgerEntry, today: date) -> str:
        if e.paid_on:
            return "paid"
        return "overdue_pcn_likely" if today > payment_window(e.day)[1] else "due"

    def deadline(self, e: LedgerEntry) -> date:
        return payment_window(e.day)[1]

    def list(self, reg: Optional[str] = None) -> list[LedgerEntry]:
        es = sorted(self._entries.values(), key=lambda e: (e.day, e.reg))
        return [e for e in es if reg is None or e.reg == reg.upper()]


def pcn_exposure(entries: list[LedgerEntry], today: date) -> dict:
    """Money at risk from unpaid, past-deadline entries: the PCN plus the outstanding charge."""
    overdue = [e for e in entries if e.paid_on is None and today > payment_window(e.day)[1]]
    return {
        "overdue_days": len(overdue),
        "outstanding_charges_gbp": round(sum(e.charge for e in overdue), 2),
        "pcn_if_paid_within_14_days_gbp": round(len(overdue) * RULES.pcn_discounted, 2),
        "pcn_full_gbp": round(len(overdue) * RULES.pcn_full, 2),
    }


def pcn_risk_score(v: Vehicle, planned_caz_entry: bool, day: date, ledger: ComplianceLedger,
                   today: date, payment_confirmed: bool = False) -> dict:
    """Transparent rule-based score 0-100 (v1). A learned model replaces the weights in Phase 3."""
    compliant = is_compliant(v)
    if compliant is True:
        return {"score": 0, "level": "none", "factors": ["vehicle compliant or exempt"]}
    score, factors = 0, []
    if compliant is None:
        score += 25
        factors.append("emission standard unknown - verify vehicle on the GOV.UK checker")
    if planned_caz_entry:
        score += 30
        factors.append("route enters the Clean Air Zone")
        if not payment_confirmed:
            score += 20
            factors.append("daily charge not yet paid/confirmed")
            hi = payment_window(day)[1]
            if today > hi:
                score += 15
                factors.append("payment window already closed - PCN likely")
            elif (hi - today).days <= 1:
                score += 10
                factors.append("payment deadline within 24h")
    stale = [e for e in ledger.list(v.reg) if e.paid_on is None and today > payment_window(e.day)[1]]
    if stale:
        score += min(15, 5 * len(stale))
        factors.append(f"{len(stale)} earlier unpaid day(s) past deadline")
    score = min(100, score)
    level = "high" if score >= 70 else "medium" if score >= 40 else "low"
    return {"score": score, "level": level, "factors": factors}
