# Launch post draft (r/selfhosted / blog / LinkedIn)

**I built an open-source "UptimeRobot for domains" — availability, price, expiration, DNS and security monitoring from one CLI.**

After realizing I was checking domain expirations by hand in a spreadsheet, I turned my
monitoring scripts into **DomainWatch** (MIT, Python):

- 🔔 Availability & price tracking (GoDaddy live + RDAP fallback), price history in SQLite
- ⏳ Expiration lifecycle alerts (registered → expiring → expired → pending delete → available)
- 🌐 DNS intelligence: A/AAAA/MX/NS/TXT/CAA/SOA/DNSSEC with change detection
- 🔐 Security audit: SPF / DMARC / CAA / DNSSEC / TLS scoring
- 🔎 Certificate Transparency monitoring + subdomain discovery
- 💸 Multi-registrar price comparison (Porkbun / Cloudflare / Namecheap / GoDaddy / Dynadot)
- 📊 FastAPI REST API, web dashboard, Prometheus `/metrics`
- 📨 Alerts to Discord / Telegram / ntfy / webhooks
- 🐳 Docker, mkdocs site, plugin SDK

```bash
pip install -e .
domain-monitor check example.com
domain-monitor audit example.com
domain-monitor serve   # dashboard + API + metrics
```

Repo: https://github.com/aavash-devkota/DomainWatch
Docs: https://aavash-devkota.github.io/DomainWatch/

Feature requests welcome — especially: new providers, new notification channels, and
pain points you've hit running monitors.
