from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from .storage.db import DB


def generate_report(db: Optional[DB] = None) -> str:
    db = db or DB()
    domains = db.list_domains()
    lines = [f"DomainWatch Report — {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}\n",
             f"{len(domains)} domains monitored\n"]
    avail_new = price_drop = expiring = dns_changes = tls_warn = 0
    since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    for d in domains:
        hist = db.history(d["domain"], limit=50)
        if hist and hist[0]["available"]:
            avail_new += 1
        prices = [h["price"] for h in hist if h["price"] is not None]
        if len(prices) >= 2 and prices[0] < prices[-1]:
            price_drop += 1
        last = db.last_check(d["domain"])
        if last and last["expiration"]:
            try:
                dt = datetime.fromisoformat(last["expiration"].replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if 0 < (dt - datetime.now(timezone.utc)).days <= 30:
                    expiring += 1
            except ValueError:
                pass
    ev = db.conn.execute(
        "SELECT type, COUNT(*) c FROM events WHERE timestamp >= ? GROUP BY type",
        (since,)).fetchall()
    ev_map = {r["type"]: r["c"] for r in ev}
    lines.append("Availability")
    lines.append(f"  {avail_new} newly available\n")
    lines.append("Pricing")
    lines.append(f"  {price_drop} price decreases in history\n")
    lines.append("Expiration")
    lines.append(f"  {expiring} domains expire within 30 days\n")
    lines.append("Events (7d)")
    for t, c in ev_map.items():
        lines.append(f"  {t}: {c}")
    if not ev_map:
        lines.append("  none")
    return "\n".join(lines)
