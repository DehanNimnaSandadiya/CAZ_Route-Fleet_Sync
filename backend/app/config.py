"""Central configuration. CAZ constants were checked against Bristol City Council / GOV.UK
pages in Oct 2026 but MUST be re-verified before production use."""
from dataclasses import dataclass


@dataclass(frozen=True)
class CazRules:
    # Class D zone live since 28 Nov 2022. Daily charge by vehicle class (GBP).
    charge_light: float = 9.0     # cars, taxis, vans/LGVs, minibuses
    charge_heavy: float = 100.0   # HGVs, buses, coaches
    # Minimum emission standards: petrol Euro 4+, diesel Euro 6+ (HGV/bus: Euro VI).
    min_petrol_euro: int = 4
    min_diesel_euro: int = 6
    # Pay up to 6 days before, or by end of the 6th day after, the day of travel.
    pay_window_days_before: int = 6
    pay_window_days_after: int = 6
    # PCN: GBP 120, 50% discount if paid in first 14 days of service; 28 days to pay.
    # The unpaid daily charge is payable in addition to the PCN.
    pcn_full: float = 120.0
    pcn_discounted: float = 60.0


RULES = CazRules()

# Routing economics (tunable per customer)
VALUE_OF_TIME_S_PER_GBP = 120.0   # 1 GBP of charge == 2 minutes of delay in the cost function
DRIVER_RATE_GBP_PER_H = 27.0
RIDER_RATE_GBP_PER_H = 22.0
HANDSHAKE_FEE_GBP = 1.20          # platform fee per parcel handed over at a micro-hub
