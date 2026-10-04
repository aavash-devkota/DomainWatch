from __future__ import annotations

import hashlib
import json
import time
from typing import Optional

from ..core.models import DomainState, Event, Severity
from ..dns import records
from ..events.bus import EventBus
from ..providers.base import Provider
from ..providers.godaddy import GoDaddyProvider
from ..providers.manager import ProviderManager
from ..providers.rdap_provider import RdapProvider
from ..storage.db import DB
from .alerts import AlertEngine
from .lifecycle import Lifecycle, classify, days_until

EXPIRING_SOON_DAYS = 30


def dns_fingerprint(domain: str) -> dict[str, str]:
    data = records.lookup(domain)
    return {t: hashlib.sha256(json.dumps(v).encode()).hexdigest()[:16]
            for t, v in data.items() if v}


class Engine:
    def __init__(self, db: Optional[DB] = None, provider: Optional[Provider] = None,
                 providers: Optional[list[Provider]] = None):
        self.db = db or DB()
        if providers is not None:
            self.providers = ProviderManager(providers)
        elif provider is not None:
            self.providers = ProviderManager([provider, RdapProvider()])
        else:
            self.providers = ProviderManager([GoDaddyProvider(), RdapProvider()])
        self.bus = EventBus()
        self.alerts = AlertEngine(self.db)

    def check_one(self, domain: str, target_price: Optional[float] = None) -> DomainState:
        state = self.providers.check(domain)
        from ..metrics import inc_check, observe_latency
        inc_check(domain, state.available, bool(state.error))
        self.db.record_check(state)
        self._diff_and_emit(state, target_price)
        self._dns_change_detection(domain)
        return state

    def _emit(self, ev: Event) -> None:
        self.db.record_event(ev.type, ev.domain, ev.message, {**ev.data, "severity": ev.severity})
        if self.alerts.process(ev):
            from ..metrics import inc_notification
            inc_notification()
            self.bus.emit(ev)

    def _diff_and_emit(self, state: DomainState, target_price: Optional[float]) -> None:
        domain = state.domain
        rows = self.db.history(domain, limit=2)
        prev = rows[1] if len(rows) >= 2 else None

        lifecycle = classify(state.available, state.expiration, state.status)
        if lifecycle == Lifecycle.PENDING_DELETE:
            self._emit(Event("PendingDeleteDetected", domain, f"{domain} is PENDING DELETE",
                             {}, Severity.CRITICAL))
        elif lifecycle == Lifecycle.EXPIRED:
            self._emit(Event("DomainExpired", domain, f"{domain} has EXPIRED", {}, Severity.CRITICAL))

        if state.available is True and (prev is None or not bool(prev["available"])):
            self._emit(Event("DomainAvailable", domain, f"{domain} is AVAILABLE",
                             {"price": state.price}, Severity.NOTICE))

        if state.price is not None and prev and prev["price"] is not None and state.price < prev["price"]:
            pct = (1 - state.price / prev["price"]) * 100
            self._emit(Event("PriceDropped", domain,
                             f"{domain} price dropped ${prev['price']:.2f} -> ${state.price:.2f} (-{pct:.0f}%)",
                             {"old_price": prev["price"], "price": state.price}, Severity.INFO))

        if target_price is not None and state.available and state.price is not None and state.price <= target_price:
            self._emit(Event("PriceBelowThreshold", domain,
                             f"{domain} available for ${state.price:.2f} (target ${target_price:.2f})",
                             {"price": state.price, "target_price": target_price}, Severity.NOTICE))

        days = days_until(state.expiration)
        if days is not None:
            if days <= 14:
                sev = Severity.WARNING
            elif days <= EXPIRING_SOON_DAYS:
                sev = Severity.NOTICE
            else:
                sev = None
            if sev:
                self._emit(Event("ExpirationApproaching", domain,
                                 f"{domain} expires in {days:.0f} days", {"days": days}, sev))
        if state.premium:
            self._emit(Event("PremiumDomain", domain, f"{domain} is premium/aftermarket", {}, Severity.INFO))

    def _dns_change_detection(self, domain: str) -> None:
        try:
            fp = dns_fingerprint(domain)
        except Exception:
            return
        rows = self.db.conn.execute(
            "SELECT record_type, hash, value FROM dns_history WHERE domain=? AND id IN "
            "(SELECT MAX(id) FROM dns_history WHERE domain=? GROUP BY record_type)",
            (domain, domain)).fetchall()
        prev = {r["record_type"]: r["hash"] for r in rows}
        for t, h in fp.items():
            if t in prev and prev[t] != h:
                sev = Severity.WARNING if t in ("NS", "MX", "CAA") else Severity.NOTICE
                self._emit(Event("DNSChanged", domain, f"{domain} {t} records changed",
                                 {"record_type": t}, sev))
            if t not in prev or prev[t] != h:
                for v in records.lookup(domain, [t]).get(t, []):
                    self.db.conn.execute(
                        "INSERT INTO dns_history(domain, record_type, value, hash) VALUES(?,?,?,?)",
                        (domain, t, v, h))
        self.db.conn.commit()

    def check_all(self) -> list[DomainState]:
        states = []
        for row in self.db.list_domains():
            if not row["enabled"]:
                continue
            states.append(self.check_one(row["domain"], row["target_price"]))
            time.sleep(1)
        return states
