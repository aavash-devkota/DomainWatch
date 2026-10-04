from __future__ import annotations

import socket
import ssl
from dataclasses import dataclass, field

from ..dns import records


@dataclass
class AuditResult:
    domain: str
    checks: dict[str, dict] = field(default_factory=dict)
    score: int = 0

    def add(self, name: str, ok: bool | None, detail: str = "", weight: int = 0):
        self.checks[name] = {"ok": ok, "detail": detail}
        if ok:
            self.score += weight

    def max_score(self) -> int:
        # weighted: dnssec 20, dmarc 20, spf 20, caa 10, https 20, mx 10
        return 100


def tls_info(domain: str, port: int = 443, timeout: int = 8) -> dict:
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((domain, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                return {"ok": True, "issuer": dict(x[0] for x in cert.get("issuer", [])).get("organizationName"),
                        "expires": cert.get("notAfter")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def audit(domain: str) -> AuditResult:
    r = AuditResult(domain=domain)
    r.add("DNSSEC", records.has_dnssec(domain), weight=20)
    spf = records.spf_record(domain)
    r.add("SPF", spf is not None, spf or "missing", weight=20)
    dmarc = records.dmarc_record(domain)
    r.add("DMARC", dmarc is not None, dmarc or "missing", weight=20)
    caa = records.caa_records(domain)
    r.add("CAA", len(caa) > 0, "; ".join(caa) if caa else "missing", weight=10)
    mx = records.lookup(domain, ["MX"]).get("MX", [])
    r.add("MX", len(mx) > 0, ", ".join(mx) if mx else "none", weight=10)
    tls = tls_info(domain)
    r.add("HTTPS/TLS", tls.get("ok"), tls.get("issuer") or tls.get("error", ""), weight=20)
    return r


def render(r: AuditResult) -> str:
    lines = [f"Domain Security Audit: {r.domain}", f"Score: {r.score}/{r.max_score()}", ""]
    for name, c in r.checks.items():
        icon = "✓" if c["ok"] else ("⚠" if c["ok"] is None else "✗")
        lines.append(f"{name:<14} {icon}  {c['detail']}")
    return "\n".join(lines)
