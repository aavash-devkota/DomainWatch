from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class Lifecycle(str, Enum):
    UNKNOWN = "unknown"
    REGISTERED = "registered"
    EXPIRING = "expiring"
    EXPIRED = "expired"
    PENDING_DELETE = "pending_delete"
    AVAILABLE = "available"


def days_until(iso: Optional[str]) -> Optional[float]:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (dt - datetime.now(timezone.utc)).total_seconds() / 86400
    except ValueError:
        return None


def classify(available: Optional[bool], expiration: Optional[str], status: Optional[str] = None) -> Lifecycle:
    s = (status or "").lower()
    if "pending delete" in s or "pendingdelete" in s:
        return Lifecycle.PENDING_DELETE
    if available is True:
        return Lifecycle.AVAILABLE
    days = days_until(expiration)
    if days is None:
        return Lifecycle.REGISTERED if available is False else Lifecycle.UNKNOWN
    if days < 0:
        return Lifecycle.EXPIRED
    if days <= 30:
        return Lifecycle.EXPIRING
    return Lifecycle.REGISTERED
