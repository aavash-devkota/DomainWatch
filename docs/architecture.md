# Architecture

```
CLI ──► Core Engine ──► Event Engine ──► Notifications
          │                  │
          ▼                  ▼
     Providers/ADAPT ──► SQLite ──► API (FastAPI) ──► Dashboard / Prometheus
```

- `domainwatch/core` — models, engine, scoring, lifecycle, alert rules
- `domainwatch/providers` — GoDaddy, RDAP, multi-registrar offers, registry
- `domainwatch/events` — pub/sub EventBus
- `domainwatch/notifications` — console, webhook, Discord, ntfy, Telegram
- `domainwatch/storage` — SQLite, migrations, repositories, team
- `domainwatch/api` — FastAPI app
- `domainwatch/security` — audit, TLS, HTTP headers
- `domainwatch/sdk` — plugin protocol + entry points
