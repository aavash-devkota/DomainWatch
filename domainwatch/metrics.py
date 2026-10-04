from __future__ import annotations

import threading
from typing import Counter, Optional

_checks_total: Counter = Counter()
_errors_total: Counter = Counter()
_notifications_total: Counter = Counter()
_provider_latency: dict[str, list[float]] = {}
_lock = threading.Lock()


def inc_check(domain: str, available: Optional[bool], error: bool) -> None:
    with _lock:
        _checks_total["total"] += 1
        if error:
            _errors_total["total"] += 1
        if available is True:
            _checks_total["available"] += 1


def inc_notification() -> None:
    with _lock:
        _notifications_total["total"] += 1


def observe_latency(provider: str, ms: float) -> None:
    with _lock:
        _provider_latency.setdefault(provider, []).append(ms)


def snapshot() -> dict:
    return {
        "checks_total": dict(_checks_total),
        "errors_total": dict(_errors_total),
        "notifications_total": dict(_notifications_total),
        "latency_avg_ms": {p: sum(v) / len(v) for p, v in _provider_latency.items()},
    }


def render_prometheus() -> str:
    from .storage.db import DB
    db = DB()
    domains = db.list_domains()
    expiring = 0
    available = 0
    from .core.lifecycle import days_until
    for d in domains:
        last = db.last_check(d["domain"])
        if last:
            if last["available"]:
                available += 1
            du = days_until(last["expiration"])
            if du is not None and 0 < du <= 30:
                expiring += 1
    snap = snapshot()
    lines = []
    lines.append(f"domainwatch_checks_total {snap['checks_total'].get('total', 0)}")
    lines.append(f"domainwatch_check_errors_total {snap['errors_total'].get('total', 0)}")
    lines.append(f"domainwatch_notifications_total {snap['notifications_total'].get('total', 0)}")
    lines.append(f"domainwatch_domains_monitored {len(domains)}")
    lines.append(f"domainwatch_domains_expiring {expiring}")
    lines.append(f"domainwatch_available_domains {available}")
    for p, avg in snap["latency_avg_ms"].items():
        lines.append(f'domainwatch_provider_latency_seconds{{provider="{p}"}} {avg/1000:.3f}')
    return "\n".join(lines) + "\n"
