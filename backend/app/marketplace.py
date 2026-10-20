"""SME pool-sharing marketplace for localised drop nodes (lockers, shop counters, loading bays)."""
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from datetime import date


@dataclass
class DropNode:
    id: str
    name: str
    host_business: str
    node_id: str
    slots_per_day: int
    price_per_slot_gbp: float
    bookings: dict[date, list["Booking"]] = field(default_factory=dict)


@dataclass
class Booking:
    id: str
    drop_node_id: str
    business: str
    day: date
    slots: int
    price_gbp: float


class Marketplace:
    PLATFORM_TAKE_RATE = 0.10    # 10% commission, shown to host and booker before confirmation

    def __init__(self) -> None:
        self.nodes: dict[str, DropNode] = {}

    def add_node(self, n: DropNode) -> None:
        self.nodes[n.id] = n

    def free_slots(self, node_id: str, day: date) -> int:
        n = self.nodes[node_id]
        used = sum(b.slots for b in n.bookings.get(day, []))
        return n.slots_per_day - used

    def book(self, node_id: str, business: str, day: date, slots: int) -> Booking:
        if slots < 1:
            raise ValueError("slots must be >= 1")
        n = self.nodes[node_id]
        if self.free_slots(node_id, day) < slots:
            raise ValueError("not enough free slots")
        b = Booking(uuid.uuid4().hex[:12], node_id, business, day, slots,
                    round(slots * n.price_per_slot_gbp, 2))
        n.bookings.setdefault(day, []).append(b)
        return b

    def quote(self, node_id: str, slots: int) -> dict:
        n = self.nodes[node_id]
        gross = round(slots * n.price_per_slot_gbp, 2)
        fee = round(gross * self.PLATFORM_TAKE_RATE, 2)
        return {"gross_gbp": gross, "platform_fee_gbp": fee, "host_payout_gbp": round(gross - fee, 2)}

    def pool_split(self, node_id: str, day: date) -> dict[str, float]:
        """Fair split of the host's daily slot cost across booked businesses (by slots used)."""
        bs = self.nodes[node_id].bookings.get(day, [])
        total = sum(b.price_gbp for b in bs)
        slots = sum(b.slots for b in bs) or 1
        out: dict[str, float] = {}
        for b in bs:
            out[b.business] = round(out.get(b.business, 0.0) + total * b.slots / slots, 2)
        return out
