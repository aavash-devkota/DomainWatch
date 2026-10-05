# DomainWatch — Operation Flow & User Guide

## Mental model

DomainWatch is a pipeline:

```
Add/track domains  →  monitor loop checks them on an interval
      ↓
Check results are diffed against history → events fire
      ↓
Events are stored (SQLite), alerted (ntfy/Discord/Telegram/webhook), and exposed via API
      ↓
You inspect the same data through: CLI · web dashboard · REST API · metrics
```

There are three ways to work, converging on the same SQLite DB:

| Path | Best for |
|---|---|
| CLI (`domain-monitor …`) | one-off actions, cron, scripting |
| Web GUI (`/dashboard`) | day-to-day viewing, running probes, settings |
| REST API / metrics | automation, Prometheus/Grafana |

---

## CLI flow

### 1. First run / setup
```bash
domain-monitor doctor            # verify everything is wired
domain-monitor db status         # schema version, migrations available
domain-monitor keys create --name admin --role admin   # if you'll enable API auth
```

### 2. Track domains with targets
```bash
domain-monitor add example.com -t 20
```

### 3. Monitor continuously (pick one)
```bash
domain-monitor watch             # live sweep view (human-friendly)
domain-monitor -c config.yaml run  # headless loop (cron/systemd)
```

### 4. Investigate results
```bash
domain-monitor status            # latest state of all
domain-monitor history example.com
domain-monitor price example.com # min/max/avg
domain-monitor timeline example.com   # events only
```

### 5. Deep-dive one domain
```bash
domain-monitor score example.com      # opportunity score
domain-monitor rdap example.com
domain-monitor dns example.com
domain-monitor tls example.com
domain-monitor http example.com
domain-monitor audit example.com      # 0-100 security score
domain-monitor ct example.com --track # new cert alerts
domain-monitor subdomains example.com
domain-monitor lifecycle example.com  # registered/expiring/...
```

### 6. Explore / compare
```bash
domain-monitor discover cyber --tlds com dev io --only-available --workers 6
domain-monitor price-compare cyberexample.com
```

### 7. Operate the system
```bash
domain-monitor report           # weekly-style summary
domain-monitor backup --output backup.db
domain-monitor export out.json  # portability
domain-monitor providers        # provider health
domain-monitor serve            # start web UI + API
```

**Config + alerts:** edit `~/.domainwatch/config.yaml` (domains with targets,
`monitor.interval`, notification channels) or set them in the GUI Settings tab.
`DW_AUTH=1` turns on API-key enforcement.

---

## GUI flow (which tab, when)

Start the server first:

```bash
domain-monitor serve            # then open http://localhost:8080/dashboard
```

| Tab | When to use it | What you do there |
|---|---|---|
| **📊 Dashboard** | You open the app / daily glance | See stat cards, price-history chart, latest events; landing view |
| **🌐 Domains** | Add/remove/inspect watched domains | Table of tracked domains with status/price/expiry/lifecycle; add with target price; per-domain instant "check" |
| **🔔 Events** | After a sweep / alert | Timeline of every event (price drops, availability, DNS changes, expiring) — filterable |
| **🛠 Tools** | Ad-hoc intelligence on one domain | Pick a domain, tick any combination of Check/Score/Audit/Compare/CT/Subdomains/TLS/HTTP/Lifecycle/DNS, run them all, filter the combined output |
| **🔌 Providers** | Health of data sources | Live provider probe + a labeled metrics table (what each Prometheus metric means) with raw scrape link |
| **🔑 Alerts & Keys** | Set up team access & review actions | Create/revoke API keys by role, browse the audit log |
| **⚙️ Settings** | Configure schedule & notifications | Interval in seconds, ntfy/Discord/Telegram credentials, save (audited), test buttons |
| **⌨ Terminal** | Power-user / quick CLI work | Real xterm.js shell embedded in the page — run any `domain-monitor` command without leaving the GUI |

### Typical GUI session

1. Open app → **Dashboard** tab → see if anything needs attention.
2. Add a domain on **Domains** (or in Settings → domains file + restart `run`).
3. Hit **check** on a row → row refreshes; a `DomainAvailable`/`PriceBelowThreshold`
   event lands in **Events**.
4. Curious? Open **Tools**, tick Audit + TLS + DNS, run, and read the cards.
5. Want alerts? Configure ntfy/Discord/Telegram in **Settings**, press test,
   then wait for the next sweep.
6. Share with a teammate? **Alerts & Keys** → create an Operator key.

---

## Where things live

| Thing | Location |
|---|---|
| Config | `~/.domainwatch/config.yaml` (edit in GUI Settings or by hand) |
| Secrets | `~/.domainwatch/.env` or env vars |
| Database | `~/.domainwatch/domainwatch.db` (SQLite; migrations in `storage/migrations/`) |
| Monitor log | stdout of `domain-monitor run` / `~/.domainwatch/monitor.log` |
| Docs site | https://aavash-devkota.github.io/DomainWatch/ |
