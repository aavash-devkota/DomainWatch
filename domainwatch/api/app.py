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


@app.get("/checks/run/{domain}")
def run_check(domain: str):
    from ..core.engine import Engine
    eng = Engine(db=db)
    st = eng.check_one(domain)
    return st.to_dict()


@app.get("/price-compare/{domain}")
def price_compare(domain: str):
    from ..providers import registry
    offers = registry.compare(domain)
    return [o.__dict__ for o in offers]


@app.get("/subdomains/{domain}")
def subdomains_ep(domain: str, resolve: bool = False):
    from .. import ct
    subs = ct.subdomains(domain)
    if not resolve:
        return {"domain": domain, "count": len(subs), "subdomains": subs}
    import socket
    out = []
    for s in subs[:100]:
        try:
            out.append({"subdomain": s, "ip": socket.gethostbyname(s)})
        except Exception:
            out.append({"subdomain": s, "ip": None})
    return {"domain": domain, "count": len(out), "subdomains": out}


@app.get("/tls/{domain}")
def tls_ep(domain: str):
    from ..security import tls
    return tls.inspect(domain).__dict__


@app.get("/http/{domain}")
def http_ep(domain: str):
    from ..security import httpmon
    return httpmon.check(domain).__dict__


@app.get("/lifecycle/{domain}")
def lifecycle_ep(domain: str):
    from ..core.lifecycle import classify
    last = db.last_check(domain)
    if not last:
        raise HTTPException(404, "no data")
    avail = None if last["available"] is None else bool(last["available"])
    return {"domain": domain, "lifecycle": classify(avail, last["expiration"], last["status"]).value,
            "expiration": last["expiration"]}


@app.get("/settings")
def get_settings():
    from ..config import load_config
    return load_config() or {}


@app.post("/settings")
def save_settings(interval: Optional[float] = None, ntfy_topic: Optional[str] = None,
                  discord_webhook: Optional[str] = None, telegram_token: Optional[str] = None,
                  telegram_chat_id: Optional[str] = None, ntfy_enabled: Optional[bool] = None,
                  discord_enabled: Optional[bool] = None, telegram_enabled: Optional[bool] = None):
    import yaml
    from ..config import DEFAULT_CONFIG, load_config
    cfg = load_config() or {}
    if interval is not None:
        cfg.setdefault("monitor", {})["interval"] = interval
    n = cfg.setdefault("notifications", {})
    def setn(key, enabled, **kv):
        sec = n.setdefault(key, {})
        if enabled is not None:
            sec["enabled"] = enabled
        for k, v in kv.items():
            if v is not None:
                sec[k] = v
    setn("ntfy", ntfy_enabled, topic=ntfy_topic)
    setn("discord", discord_enabled, webhook=discord_webhook)
    setn("telegram", telegram_enabled, token=telegram_token, chat_id=telegram_chat_id)
    DEFAULT_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    with DEFAULT_CONFIG.open("w") as f:
        yaml.safe_dump(cfg, f)
    from ..storage.team import audit
    audit(db.conn, "gui", "save_settings", "config")
    return {"saved": True, "config": cfg}


@app.post("/test-alert")
def test_alert(channel: str = "console"):
    from ..core.models import Event
    from ..notifications.base import ConsoleNotifier, DiscordNotifier, NtfyNotifier, TelegramNotifier
    from ..config import load_config, get
    cfg = load_config()
    ev = Event("TestAlert", "example.com", f"DomainWatch test alert via {channel}")
    try:
        if channel == "discord":
            DiscordNotifier(get(cfg, "notifications", "discord", "webhook", default="")).send(ev)
        elif channel == "ntfy":
            NtfyNotifier(get(cfg, "notifications", "ntfy", "topic", default="")).send(ev)
        elif channel == "telegram":
            TelegramNotifier(get(cfg, "notifications", "telegram", "token", default=""),
                             str(get(cfg, "notifications", "telegram", "chat_id", default=""))).send(ev)
        else:
            ConsoleNotifier().send(ev)
        return {"sent": channel}
    except Exception as e:
        raise HTTPException(400, str(e))


@app.get("/metrics")
def metrics():
    from fastapi.responses import PlainTextResponse
    from ..metrics import render_prometheus
    return PlainTextResponse(render_prometheus(), media_type="text/plain; version=0.0.4")


DASHBOARD_HTML = r"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>DomainWatch</title>
<style>
*{box-sizing:border-box}body{font-family:ui-monospace,monospace;background:#0d1117;color:#c9d1d9;margin:0;padding:1.5em}
h1{margin-top:0}.card{display:inline-block;border:1px solid #30363d;border-radius:8px;padding:1em 1.6em;margin:.4em;text-align:center;min-width:130px}
.num{font-size:1.8em;color:#58a6ff}.tab{display:inline-block;padding:.5em 1em;border:1px solid #30363d;border-radius:6px;margin:.2em;cursor:pointer}
.tab.active{background:#1f6feb;border-color:#1f6feb;color:#fff}section{border:1px solid #30363d;border-radius:8px;padding:1em;margin-top:1em;display:none}
section.active{display:block}table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #21262d;padding:.45em .7em;text-align:left}
.ok{color:#3fb950}.bad{color:#f85149}.warn{color:#d29922}input,button,select{background:#161b22;border:1px solid #30363d;color:#c9d1d9;border-radius:6px;padding:.4em .7em;margin:.2em}
button{cursor:pointer}button:hover{background:#1f6feb;color:#fff}pre{white-space:pre-wrap;background:#161b22;border-radius:6px;padding:.8em;overflow-x:auto}
</style></head><body>
<h1>DomainWatch <small style="color:#8b949e;font-size:.6em">intelligence platform</small></h1>
<div id="summary"></div>
<div>
<span class="tab active" onclick="show('domains',this)">Domains</span>
<span class="tab" onclick="show('events',this)">Events</span>
<span class="tab" onclick="show('tools',this)">Tools</span>
<span class="tab" onclick="show('providers',this)">Providers</span>
<span class="tab" onclick="show('alerts',this)">Alerts & Keys</span>
<span class="tab" onclick="show('settings',this)">Settings</span>
</div>

<section id="domains" class="active">
<h2>Tracked domains</h2>
<input id="nd" placeholder="example.com"><input id="nt" placeholder="target $" type="number">
<button onclick="addDomain()">Add</button>
<table id="dtable"><tr><th>Domain</th><th>Status</th><th>Price</th><th>Expires</th><th>Lifecycle</th><th></th></tr></table>
</section>

<section id="events"><h2>Events</h2><button onclick="loadEvents()">Refresh</button><table id="etable"><tr><th>Time</th><th>Type</th><th>Message</th></tr></table></section>

<section id="tools">
<h2>Tools</h2>
Domain: <input id="tdom" placeholder="example.com">
<button onclick="probe('check')">Check</button>
<button onclick="probe('score')">Score</button>
<button onclick="probe('audit')">Audit</button>
<button onclick="probe('price-compare')">Compare price</button>
<button onclick="probe('ct')">CT / Certificates</button>
<button onclick="probe('subdomains')">Subdomains</button>
<button onclick="probe('tls')">TLS</button>
<button onclick="probe('http')">HTTP</button>
<button onclick="probe('lifecycle')">Lifecycle</button>
<button onclick="probe('dns')">DNS</button>
<pre id="toolout">Pick a domain and a tool…</pre>
</section>

<section id="providers"><h2>Provider health</h2><button onclick="loadProviders()">Probe</button><pre id="provout"></pre></section>

<section id="alerts">
<h2>API keys</h2>
<input id="kn" placeholder="name"><select id="kr"><option>viewer</option><option>operator</option><option>admin</option><option>auditor</option></select>
<button onclick="createKey()">Create key</button>
<button onclick="loadKeys()">Refresh</button>
<table id="ktable"><tr><th>Name</th><th>Role</th><th>Team</th><th>Revoked</th></tr></table>
<h2>Audit log</h2><button onclick="loadAudit()">Refresh</button><table id="atable"><tr><th>Time</th><th>Actor</th><th>Action</th><th>Target</th></tr></table>
</section>

<section id="settings">
<h2>Monitoring schedule & alerting</h2>
Check interval (seconds): <input id="s_interval" type="number" value="300"><br>
<h3>ntfy</h3>Topic URL: <input id="s_ntfy" placeholder="https://ntfy.sh/mytopic"> Enabled: <input id="s_ntfy_on" type="checkbox"><br>
<h3>Discord</h3>Webhook: <input id="s_discord" placeholder="https://discord.com/api/webhooks/..."> Enabled: <input id="s_discord_on" type="checkbox"><br>
<h3>Telegram</h3>Token: <input id="s_tg" placeholder="BOT_TOKEN"> Chat ID: <input id="s_tgc" placeholder="12345"> Enabled: <input id="s_tg_on" type="checkbox"><br>
<button onclick="saveSettings()">Save settings</button>
<button onclick="testAlert('console')">Test: console</button>
<button onclick="testAlert('ntfy')">Test: ntfy</button>
<button onclick="testAlert('discord')">Test: discord</button>
<button onclick="testAlert('telegram')">Test: telegram</button>
<pre id="setout"></pre>
</section>

<script>
function show(id, el){document.querySelectorAll('section').forEach(s=>s.classList.remove('active'));document.getElementById(id).classList.add('active');document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));el.classList.add('active');}
async function api(u,opts){const r=await fetch(u,opts);return r.json();}
async function loadSummary(){const d=await api('/domains');let expiring=0,avail=0;for(const x of d){const l=await api('/checks/'+x.domain+'?limit=1').catch(()=>null);}
document.getElementById('summary').innerHTML=`<div class="card"><div class="num">${d.length}</div>Domains</div><div class="card"><a href="/events" style="color:#58a6ff">Events</a></div><div class="card"><a href="/metrics" style="color:#58a6ff">Metrics</a></div>`;}
async function loadDomains(){const d=await api('/domains');const t=document.getElementById('dtable');t.innerHTML='<tr><th>Domain</th><th>Status</th><th>Price</th><th>Expires</th><th>Lifecycle</th><th></th></tr>';
for(const x of d){const last=await api('/checks/'+x.domain+'?limit=1').catch(()=>null);const h=last&&last[0]?last[0]:{};
const av=h.available===1?'<span class="ok">AVAILABLE</span>':(h.available===0?'<span class="bad">taken</span>':'?');
t.innerHTML+=`<tr><td>${x.domain}</td><td>${av}</td><td>${h.price?('$'+h.price):'-'}</td><td>${h.expiration||'-'}</td><td>${h.status||'-'}</td><td><button onclick="checkNow('${x.domain}')">check</button> <button onclick="del('${x.domain}')">✕</button></td></tr>`;}}
async function addDomain(){const n=document.getElementById('nd').value;const t=document.getElementById('nt').value;if(!n)return;await api('/domains?domain='+encodeURIComponent(n)+(t?'&target_price='+t:''),{method:'POST'});loadDomains();}
async function del(d){await api('/domains/'+d,{method:'DELETE'});loadDomains();}
async function checkNow(d){await api('/checks/run/'+d);loadDomains();}
async function loadEvents(){const e=await api('/events');const t=document.getElementById('etable');t.innerHTML='<tr><th>Time</th><th>Type</th><th>Message</th></tr>';e.forEach(x=>t.innerHTML+=`<tr><td>${x.timestamp}</td><td>${x.type}</td><td>${x.message}</td></tr>`);}
async function probe(what){const d=document.getElementById('tdom').value;if(!d)return alert('enter a domain');
document.getElementById('toolout').textContent='loading…';
const map={check:'/checks/run/',score:'/score/',audit:'/audit/','price-compare':'/price-compare/',ct:'/certificates/',subdomains:'/subdomains/',tls:'/tls/',http:'/http/',lifecycle:'/lifecycle/',dns:'/dns/'};
try{const r=await api(map[what]+d);document.getElementById('toolout').textContent=JSON.stringify(r,null,2);}catch(e){document.getElementById('toolout').textContent='error: '+e;}}
async function loadProviders(){const r=await fetch('/metrics');document.getElementById('provout').textContent=await r.text();}
async function createKey(){const n=document.getElementById('kn').value;const r=document.getElementById('kr').value;const res=await api(`/keys?name=${n}&role=${r}`,{method:'POST'});alert('New key: '+res.key);loadKeys();}
async function loadKeys(){const k=await api('/keys');const t=document.getElementById('ktable');t.innerHTML='<tr><th>Name</th><th>Role</th><th>Team</th><th>Revoked</th></tr>';k.forEach(x=>t.innerHTML+=`<tr><td>${x.name}</td><td>${x.role}</td><td>${x.team}</td><td>${x.revoked}</td></tr>`);}
async function loadAudit(){const a=await api('/audit?limit=50');const t=document.getElementById('atable');t.innerHTML='<tr><th>Time</th><th>Actor</th><th>Action</th><th>Target</th></tr>';a.forEach(x=>t.innerHTML+=`<tr><td>${x.timestamp}</td><td>${x.actor}</td><td>${x.action}</td><td>${x.target}</td></tr>`);}
loadSummary();loadDomains();loadEvents();loadSettings();
async function loadSettings(){try{const c=await api('/settings');document.getElementById('s_interval').value=(c.monitor&&c.monitor.interval)||300;
const n=c.notifications||{};const nz=n.ntfy||{};document.getElementById('s_ntfy').value=nz.topic||'';document.getElementById('s_ntfy_on').checked=!!nz.enabled;
const d=n.discord||{};document.getElementById('s_discord').value=d.webhook||'';document.getElementById('s_discord_on').checked=!!d.enabled;
const t=n.telegram||{};document.getElementById('s_tg').value=t.token||'';document.getElementById('s_tgc').value=t.chat_id||'';document.getElementById('s_tg_on').checked=!!t.enabled;}catch(e){}}
async function saveSettings(){const p=new URLSearchParams();p.set('interval',document.getElementById('s_interval').value);
p.set('ntfy_topic',document.getElementById('s_ntfy').value);p.set('ntfy_enabled',document.getElementById('s_ntfy_on').checked);
p.set('discord_webhook',document.getElementById('s_discord').value);p.set('discord_enabled',document.getElementById('s_discord_on').checked);
p.set('telegram_token',document.getElementById('s_tg').value);p.set('telegram_chat_id',document.getElementById('s_tgc').value);p.set('telegram_enabled',document.getElementById('s_tg_on').checked);
document.getElementById('setout').textContent=JSON.stringify(await api('/settings?'+p.toString(),{method:'POST'}),null,2);}
async function testAlert(ch){document.getElementById('setout').textContent=JSON.stringify(await api('/test-alert?channel='+ch,{method:'POST'}),null,2);}
</script></body></html>"""


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse(DASHBOARD_HTML)


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
