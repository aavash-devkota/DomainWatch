# Changelog

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
