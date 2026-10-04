from __future__ import annotations

import socket
import ssl
from dataclasses import dataclass, field


@dataclass
class TLSInfo:
    domain: str
    ok: bool
    issuer: str = ""
    subject: str = ""
    sans: list[str] = field(default_factory=list)
    not_before: str = ""
    not_after: str = ""
    days_remaining: float | None = None
    version: str = ""
    error: str = ""


def inspect(domain: str, port: int = 443, timeout: int = 8) -> TLSInfo:
    info = TLSInfo(domain=domain, ok=False)
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((domain, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                info.ok = True
                info.version = ssock.version() or ""
                subj = dict(x[0] for x in cert.get("subject", []))
                info.subject = subj.get("commonName", "")
                info.issuer = dict(x[0] for x in cert.get("issuer", [])).get("organizationName", "")
                info.sans = [v for k, v in cert.get("subjectAltName", []) if k == "DNS"]
                info.not_before = cert.get("notBefore", "")
                info.not_after = cert.get("notAfter", "")
                from datetime import datetime, timezone
                try:
                    exp = datetime.strptime(info.not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
                    info.days_remaining = (exp - datetime.now(timezone.utc)).total_seconds() / 86400
                except ValueError:
                    pass
    except Exception as e:
        info.error = str(e)
    return info
