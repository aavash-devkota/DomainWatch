# API

Start: `domain-monitor serve --port 8080`

| Endpoint | Description |
|---|---|
| GET /domains | list tracked |
| POST /domains | add (audited) |
| DELETE /domains/{d} | remove |
| GET /checks/{d} | check history |
| GET /events | recent events |
| GET /prices/{d} | price stats + series |
| GET /dns/{d} | DNS records |
| GET /certificates/{d} | CT entries |
| GET /alerts | events feed |
| GET /providers | provider list |
| GET /score/{d} | opportunity score |
| GET /audit/{d} | security audit |
| GET /price-compare/{d} | multi-registrar prices |
| GET /checks/run/{d} | live check |
| GET /tls/{d}, /http/{d}, /lifecycle/{d}, /subdomains/{d} | extra probes |
| GET /metrics | Prometheus |
| GET /dashboard | web UI |
| GET /terminal-ui + WS /ws/terminal | web terminal |
| POST /terminal | allowlisted CLI exec |
| GET/POST /settings, POST /test-alert | schedule + alerting config |
| GET /keys, POST /keys, GET /audit | team admin |

Auth: set `DW_AUTH=1` and pass `X-API-Key` header.
