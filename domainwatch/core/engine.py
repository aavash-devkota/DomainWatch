from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional

from ..core.models import DomainState, Event
from ..events.bus import EventBus
from ..providers.base import Provider
from ..providers.godaddy import GoDaddyProvider
from ..providers.rdap_provider import RdapProvider
from ..storage.db import DB

EXPIRING_SOON_DAYS = 30


def _days_until(iso: Optional[str]) -> Optional[float]:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (dt - datetime.now(timezone.utc)).total_seconds() / 86400
    except ValueError:
        return None


class Engine:
    def __init__(self, db: Optional[DB] = None, provider: Optional[Provider] = None):
        self.db = db or DB()
        self.provider = provider or GoDaddyProvider()
        self.fallback = RdapProvider()
        self.bus = EventBus()

    def check_one(self, domain: str, target_price: Optional[float] = None) -> DomainState:
        state = self.provider.check(domain)
        if state.error:
            fb = self.fallback.check(domain)
            if not fb.error:
                fb.price = state.price
                state = fb
        self.db.record_check(state)
        self._diff_and_emit(state, target_price)
        return state

    def _diff_and_emit(self, state: DomainState, target_price: Optional[float]) -> None:
        domain = state.domain
        prev = None
        rows = self.db.history(domain, limit=2)
        if len(rows) >= 2:
            prev = rows[1]

        if state.available is True:
            was_avail = bool(prev["available"]) if prev and prev["available"] is not None else None
            if was_avail is not True:
                self._emit(Event("DomainAvailable", domain, f"{domain} is AVAILABLE",
                                 {"price": state.price}))
        if state.price is not None and prev and prev["price"] is not None:
            if state.price < prev["price"]:
                pct = (1 - state.price / prev["price"]) * 100
                self._emit(Event("PriceDropped", domain,
                                 f"{domain} price dropped {prev['price']} -> ${state.price:.2f} (-{pct:.0f}%)",
                                 {"old": prev["price"], "new": state.price}))
        if target_price is not None and state.price is not None and state.available:
            if state.price <= target_price:
                self._emit(Event("PriceBelowThreshold", domain,
                                 f"{domain} available for ${state.price:.2f} (target ${target_price:.2f})",
                                 {"price": state.price, "target": target_price}))
        days = _days_until(state.expiration)
        if days is not None and 0 < days <= EXPIRING_SOON_DAYS:
            self._emit(Event("ExpirationApproaching", domain,
                             f"{domain} expires in {days:.0f} days ({state.expiration})",
                             {"days": days}))
        if state.premium:
            self._emit(Event("PremiumDomain", domain, f"{domain} is a premium/aftermarket name", {}))

    def _emit(self, ev: Event) -> None:
        self.db.record_event(ev.type, ev.domain, ev.message, ev.data)
        self.bus.emit(ev)

    def check_all(self, target: Optional[dict[str, float]] = None) -> list[DomainState]:
        states = []
        for row in self.db.list_domains():
            if not row["enabled"]:
                continue
            t = (target or {}).get(row["domain"], row["target_price"])
            states.append(self.check_one(row["domain"], t))
            time.sleep(1)
        return states
