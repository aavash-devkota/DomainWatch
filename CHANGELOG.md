# Changelog

## v1.4.0 (2026-10-04)
- Real interactive terminal in the web UI: xterm.js frontend + WebSocket + pexpect PTY of `/bin/bash`, fit addon, embedded via `/terminal-ui` iframe in the Dashboard Terminal tab

## v1.3.0 (2026-10-04)
- Web terminal page in the dashboard (⌘ Terminal tab) with scrollback, clear, Enter-to-run
- `/terminal` POST endpoint runs domain-monitor subcommands only (allowlist, no shell operators/redirects), 60s timeout

## v1.2.0 (2026-10-04)
- Dashboard redesign: left sidebar navigation (Dashboard/Domains/Events/Tools/Providers/Alerts & Keys/Settings), live clock, glassmorphism panels with blur, badge pills for status, canvas price chart, hover row highlight, toast notifications, overview landing page with stat cards and mini event feed

## v1.1.3 (2026-10-04)
- Tools tab is multi-select: checkboxes for every tool, Select all / Clear buttons, and "Run selected" executes the chosen set and concatenates labeled results

## v1.1.2 (2026-10-04)
- UI refresh: gradient header, glass cards, pill tabs, hover states, softer dark palette
- Selective results: live filter boxes on tables + tool output in the GUI; `--only-available` and `--workers N` concurrency for `check` and `discover` in the CLI

## v1.1.1 (2026-10-04)
- GUI Settings tab: check-interval control, per-channel notification setup (ntfy/Discord/Telegram), and one-click test alerts; backed by new `/settings` (GET/POST) and `/test-alert` endpoints; config edits audited

## v1.1.0 (2026-10-04)
- Interactive dashboard SPA: tabbed UI (Domains / Events / Tools / Providers / Alerts & Keys), add/remove domains, per-domain check button, probe any tool (check/score/audit/price-compare/CT/subdomains/TLS/HTTP/lifecycle/DNS), provider health probe, API key creation, audit log view
- New API endpoints: `/checks/run/{domain}`, `/price-compare/{domain}`, `/subdomains/{domain}`, `/tls/{domain}`, `/http/{domain}`, `/lifecycle/{domain}`

## v1.0.1 (2026-10-04)
- Check results enriched from RDAP (registrar/expiration/nameservers/status) when provider omits them — `check` now prints taken-domain registrar+expiry
- `lifecycle` command uses RDAP availability/status for live lookups
- CT lookup returns empty gracefully for domains with no CT entries (no more spurious error)
- `watch` prints sweep progress immediately

## v1.0.0 (2026-10-04)
- Dockerfile + docker-compose (serve on :8080, SQLite volume)
- CI: ruff + pytest across Python 3.10/3.12, dependabot, docs deploy to GitHub Pages
- MkDocs Material documentation site (install, CLI, config, API, architecture, contributing)

## v0.7.0 (2026-10-04)
- Team support: API keys with roles (admin/operator/viewer/auditor), audit log table, `/keys` + `/audit` endpoints, `domain-monitor keys` CLI, `DW_AUTH=1` enforces keys

## v0.6.4 (2026-10-04)
- Plugin SDK: Provider/Notifier protocols, entry-point discovery (domainwatch.providers/notifiers), engine auto-loads provider plugins

## v0.6.3 (2026-10-04)
- `domain-monitor report`: scheduled-report generator (monitored count, availability, price decreases, expiring, 7d event breakdown)

## v0.6.2 (2026-10-04)
- Prometheus `/metrics` endpoint + in-memory counters (checks, errors, notifications, provider latency, domains)

## v0.6.1 (2026-10-04)
- Web dashboard at `/dashboard`: stat cards (domains, recent events, expiring ≤30d, available), price-history sparkline, recent events feed
- SQLite `check_same_thread=False` fix for API thread handling

## v0.6.0 (2026-10-04)
- REST API via FastAPI (`domain-monitor serve`): /domains, /checks, /events, /prices, /dns, /certificates, /alerts, /providers, /score, /audit
- TestClient tests (11 passing)

## v0.5.2 (2026-10-04)
- Certificate Transparency monitoring: `domain-monitor ct` (crt.sh with certspotter fallback), `--track` baseline with NEW CERTIFICATE alerts, `ct_seen` migration
- Subdomain discovery via CT SAN aggregation: `domain-monitor subdomains [--resolve]`

## v0.5.1 (2026-10-04)
- Domain Opportunity Score (`domain-monitor score`): transparent, config-overridable weights for availability/price/TLD/brandability/history/risk; `discover` output now ranks by score

## v0.5.0 (2026-10-04)
- Provider architecture finalized: base Provider, GoDaddy, RDAP, plus multi-registrar offer providers (Porkbun/Cloudflare/Namecheap/Dynadot) via providers/registry.py
- Normalized DomainOffer model (register/renew/transfer/currency/premium/source)
- `domain-monitor price-compare` with live-or-catalog pricing and RDAP availability

## v0.4.0 (2026-10-04)
- Database migrations + `domain-monitor db migrate|status|backup`
- ProviderManager with health/fallback/latency stats (`domain-monitor providers`)
- Typed events with severity, alert rules, cooldown deduplication
- Domain lifecycle state machine (`domain-monitor lifecycle`)
- `domain-monitor watch` long-running UX, `domain-monitor doctor`
- export/import (json/csv/yaml), `domain-monitor backup`
- TLS certificate inspection (`domain-monitor tls`), HTTP security headers (`domain-monitor http`)
- DNS change detection with fingerprints

## v0.3.0 (2026-10-04)
- Project scaffold: DomainWatch package, CLI (`domain-monitor`), SQLite storage,
  event engine, provider layer (GoDaddy via gddy + RDAP fallback), RDAP module,
  DNS intelligence, security audit, notifications (console/webhook/Discord/ntfy/Telegram),
  adaptive scheduler with backoff+jitter, YAML config with env expansion, examples.

## v0.1.0
- Initial script: GoDaddy availability/price check, whois fallback, interval monitoring,
  target-price alerts.
