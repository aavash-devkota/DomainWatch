# DomainWatch

Open-source domain availability, price, expiration, DNS and security monitoring platform.

Think "UptimeRobot for domains": it watches availability, prices, expiration and DNS
posture, stores everything in SQLite, and fires alerts to Telegram/Discord/ntfy/webhooks.

## Install

```bash
pip install -e .
domain-monitor --help
```

GoDaddy pricing uses the `gddy` CLI (`gddy auth login`). Without it, RDAP is used as a
free fallback for availability/registrar/expiry.

## Usage

```bash
domain-monitor check example.com           # one-off availability/price check
domain-monitor add example.com -t 15       # track with target price
domain-monitor list                        # tracked domains
domain-monitor status                      # latest state of all
domain-monitor monitor example.com -i 300  # continuous monitoring
domain-monitor run -c config.yaml          # from config file
domain-monitor history example.com         # past checks
domain-monitor price example.com           # price stats (min/max/avg)
domain-monitor expiration example.com      # expiry date
domain-monitor rdap example.com            # registrar, nameservers, status
domain-monitor dns example.com             # A/AAAA/MX/NS/TXT/CAA/SOA
domain-monitor audit example.com           # SPF/DMARC/DNSSEC/CAA/TLS security audit
domain-monitor discover example            # candidate name discovery
domain-monitor timeline example.com        # event timeline
```

## Config (`config.yaml`)

```yaml
monitor:
  interval: 300
domains:
  - domain: example.com
    target_price: 15
notifications:
  discord:
    enabled: true
    webhook: ${DISCORD_WEBHOOK}
```

Secrets go in `.env` — never in YAML.

## Architecture

```
        CLI
         │
    Core Engine ──► SQLite (storage)
         │
  Event Engine ──► Notifications (console/telegram/discord/ntfy/webhook)
         │
 Providers (GoDaddy, RDAP)   RDAP   DNS engine
```

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

## License

MIT
