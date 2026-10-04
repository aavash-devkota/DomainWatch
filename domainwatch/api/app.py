from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

from .. import __version__
from ..storage.db import DB

app = FastAPI(title="DomainWatch API", version=__version__)
db = DB()


def rows(rs):
    return [dict(r) for r in rs]


def require_role(min_role: str):
    from fastapi import Header, HTTPException as _HE
    from ..storage.team import validate_key, ROLE_RANK
    import os

    def dep(x_api_key: Optional[str] = Header(default=None)):
        if os.environ.get("DW_AUTH", "").lower() not in ("1", "true", "yes"):
            return None  # auth disabled by default (single-user mode)
        if not x_api_key:
            raise _HE(401, "missing X-API-Key")
        row = validate_key(db.conn, x_api_key)
        if row is None:
            raise _HE(403, "invalid or revoked key")
        if ROLE_RANK[row["role"]] < ROLE_RANK[min_role]:
            raise _HE(403, f"requires role {min_role}+")
        return row
    return dep


@app.get("/metrics")
def metrics():
    from fastapi.responses import PlainTextResponse
    from ..metrics import render_prometheus
    return PlainTextResponse(render_prometheus(), media_type="text/plain; version=0.0.4")


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    from ..core.lifecycle import days_until
    domains = rows(db.list_domains())
    alerts = rows(db.events(limit=10))
    expiring = 0
    available = 0
    for d in domains:
        last = db.last_check(d["domain"])
        if last:
            if last["available"]:
                available += 1
            du = days_until(last["expiration"])
            if du is not None and 0 < du <= 30:
                expiring += 1
    price_series = []
    if domains:
        hist = rows(db.history(domains[0]["domain"], limit=200))
        price_series = [h["price"] for h in reversed(hist) if h["price"] is not None]
    # sparkline
    spark = ""
    if price_series:
        mx = max(price_series) or 1
        spark = "".join("▁▂▃▄▅▆▇█"[int((p / mx) * 7)] for p in price_series)
    events_html = "".join(f"<li>⚠/★ {e['timestamp']} — {e['message']}</li>" for e in alerts) or "<li>none</li>"
    html = f"""<html><head><title>DomainWatch</title>
<style>body{{font-family:monospace;background:#0d1117;color:#c9d1d9;margin:2em}}
.card{{display:inline-block;border:1px solid #30363d;border-radius:8px;padding:1em 2em;margin:.5em;text-align:center}}
.num{{font-size:2em;color:#58a6ff}}</style></head><body>
<h1>DomainWatch</h1>
<div class="card"><div class="num">{len(domains)}</div>Domains</div>
<div class="card"><div class="num">{len(alerts)}</div>Recent Events</div>
<div class="card"><div class="num">{expiring}</div>Expiring ≤30d</div>
<div class="card"><div class="num">{available}</div>Available</div>
<h3>Price History ({domains[0]['domain'] if domains else '-'}):</h3>
<pre style="font-size:1.4em;color:#3fb950">{spark or 'no data'}</pre>
<h3>Recent Events</h3><ul>{events_html}</ul>
</body></html>"""
    return HTMLResponse(html)


@app.get("/")
def root():
    return {"service": "DomainWatch", "version": __version__,
            "endpoints": ["/domains", "/checks/{domain}", "/events", "/prices/{domain}",
                          "/dns/{domain}", "/certificates/{domain}", "/alerts", "/providers",
                          "/score/{domain}", "/audit/{domain}"]}


@app.get("/domains")
def list_domains():
    return rows(db.list_domains())


@app.post("/domains", dependencies=[])
def add_domain(domain: str, target_price: Optional[float] = None):
    from ..storage.team import audit
    audit(db.conn, "api", "add_domain", domain)
    db.add_domain(domain, target_price)
    return {"added": domain}


@app.delete("/domains/{domain}")
def remove_domain(domain: str):
    from ..storage.team import audit
    audit(db.conn, "api", "remove_domain", domain)
    db.remove_domain(domain)
    return {"removed": domain}


@app.get("/keys")
def list_api_keys():
    from ..storage.team import list_keys
    return [dict(r) for r in list_keys(db.conn)]


@app.post("/keys")
def create_api_key(name: str, role: str = "viewer", team: str = "default"):
    from ..storage.team import create_key, audit
    key = create_key(db.conn, name, role, team)
    audit(db.conn, "api", "create_key", name, role)
    return {"key": key, "name": name, "role": role, "team": team}


@app.get("/audit")
def audit_logs(limit: int = 50):
    from ..storage.team import audit_log
    return [dict(r) for r in audit_log(db.conn, limit)]


@app.get("/checks/{domain}")
def checks(domain: str, limit: int = Query(50, ge=1, le=500)):
    h = rows(db.history(domain, limit=limit))
    if not h:
        raise HTTPException(404, "no history")
    return h


@app.get("/events")
def events(domain: Optional[str] = None, limit: int = 50):
    return rows(db.events(domain, limit=limit))


@app.get("/prices/{domain}")
def prices(domain: str):
    stats = db.price_stats(domain)
    hist = rows(db.history(domain, limit=500))
    return {"stats": stats,
            "series": [{"timestamp": h["timestamp"], "price": h["price"]} for h in reversed(hist) if h["price"] is not None]}


@app.get("/dns/{domain}")
def dns(domain: str):
    from ..dns import records
    return records.lookup(domain)


@app.get("/certificates/{domain}")
def certificates(domain: str):
    from .. import ct
    try:
        return [e.__dict__ for e in ct.fetch(domain, limit=20)]
    except Exception as e:
        raise HTTPException(502, str(e))


@app.get("/alerts")
def alerts(limit: int = 50):
    return rows(db.events(limit=limit))


@app.get("/providers")
def providers():
    from ..providers import registry
    return {"providers": [p.name for p in registry.all_providers()]}


@app.get("/score/{domain}")
def score(domain: str):
    from ..core.engine import Engine
    from ..core.score import score_domain
    eng = Engine(db=db)
    st = eng.check_one(domain)
    return score_domain(domain, st.available, st.price, st.premium).__dict__


@app.get("/audit/{domain}")
def audit(domain: str):
    from ..security.audit import audit as run
    r = run(domain)
    return {"domain": r.domain, "score": r.score, "checks": r.checks}
