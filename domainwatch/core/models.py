from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


@dataclass
class DomainState:
    domain: str
    available: Optional[bool] = None
    price: Optional[float] = None
    renewal_price: Optional[float] = None
    currency: str = "USD"
    registrar: Optional[str] = None
    premium: Optional[bool] = None
    expiration: Optional[str] = None
    status: Optional[str] = None           # e.g. active / expired / pending delete
    nameservers: list[str] = field(default_factory=list)
    dnssec: Optional[bool] = None
    provider: Optional[str] = None
    definitive: Optional[bool] = None
    error: Optional[str] = None
    checked_at: str = field(default_factory=utcnow)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["nameservers"] = ",".join(self.nameservers)
        return d


@dataclass
class Event:
    type: str          # DomainAvailable, PriceDropped, PriceBelowThreshold, ExpirationApproaching, ...
    domain: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)

    def pretty(self) -> str:
        return f"[{datetime.fromtimestamp(self.ts):%Y-%m-%d %H:%M:%S}] {self.type}: {self.message}"
