# Changelog

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
