# Configuration

`~/.domainwatch/config.yaml`:

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
scoring:
  weights:
    price: 25
```

Secrets via `.env` or environment — never in YAML. `DW_AUTH=1` enforces API keys.
Database at `~/.domainwatch/domainwatch.db`.
