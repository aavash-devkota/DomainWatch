from __future__ import annotations

import time
from typing import Any, Optional

from .models import Event, Severity

# cooldown seconds per event type (default 1h)
DEFAULT_COOLDOWNS: dict[str, float] = {
    "DomainAvailable": 3600,
    "PriceDropped": 3600,
    "PriceBelowThreshold": 3600,
    "ExpirationApproaching": 86400,
    "DomainExpired": 86400,
    "PendingDeleteDetected": 86400,
    "NameserverChanged": 86400,
    "DNSChanged": 86400,
    "DNSSECChanged": 86400,
    "SPFChanged": 86400,
    "DMARCChanged": 86400,
    "TLSChanged": 86400,
    "PremiumDomain": 86400,
}


class AlertRule:
    def __init__(self, name: str, event: str, condition: Optional[dict], notify: list[str],
                 severity: Optional[list[str]] = None):
        self.name = name
        self.event = event
        self.condition = condition or {}
        self.notify = notify or []
        self.severity = severity or []

    @classmethod
    def from_dict(cls, d: dict) -> "AlertRule":
        return cls(d.get("name", d.get("event", "rule")), d.get("event", "*"),
                   d.get("condition"), d.get("notify", []), d.get("severity"))

    def matches(self, ev: Event) -> bool:
        if self.event not in ("*", ev.type):
            return False
        if self.severity and ev.severity not in self.severity:
            return False
        c = self.condition
        if "price_lte" in c:
            price = ev.data.get("price") or ev.data.get("new_price")
            if price is None or price > c["price_lte"]:
                return False
        if "days_remaining_lte" in c:
            days = ev.data.get("days")
            if days is None or days > c["days_remaining_lte"]:
                return False
        return True


class AlertEngine:
    """Applies rules + dedup/cooldown, returns events that should notify."""

    def __init__(self, db, rules: Optional[list[AlertRule]] = None,
                 cooldowns: Optional[dict[str, float]] = None):
        self.db = db
        self.rules = rules or []
        self.cooldowns = {**DEFAULT_COOLDOWNS, **(cooldowns or {})}

    def should_notify(self, ev: Event) -> bool:
        cd = self.cooldowns.get(ev.type, 3600)
        recent = self.db.recent_event(ev.type, ev.domain, cd)
        return recent is None

    def process(self, ev: Event) -> bool:
        """Returns True if the event should be delivered."""
        if self.rules:
            if not any(r.matches(ev) for r in self.rules):
                return False
        return self.should_notify(ev)
