from __future__ import annotations

import time
from dataclasses import dataclass, field

import requests

SECURITY_HEADERS = ["strict-transport-security", "content-security-policy",
                    "x-content-type-options", "x-frame-options", "referrer-policy",
                    "permissions-policy"]


@dataclass
class HTTPReport:
    url: str
    ok: bool
    status: int | None = None
    elapsed_ms: float | None = None
    https_redirect: bool | None = None
    headers: dict[str, str] = field(default_factory=dict)
    missing_headers: list[str] = field(default_factory=list)
    error: str = ""


def check(domain: str, timeout: int = 10) -> HTTPReport:
    rep = HTTPReport(url=f"https://{domain}", ok=False)
    try:
        t0 = time.monotonic()
        r = requests.get(f"https://{domain}", timeout=timeout, allow_redirects=True)
        rep.elapsed_ms = (time.monotonic() - t0) * 1000
        rep.status = r.status_code
        rep.ok = r.status_code < 500
        rep.headers = {k.lower(): v for k, v in r.headers.items()}
        rep.missing_headers = [h for h in SECURITY_HEADERS if h not in rep.headers]
        # http->https redirect?
        h = requests.get(f"http://{domain}", timeout=timeout, allow_redirects=False)
        rep.https_redirect = h.status_code in (301, 302, 307, 308) and \
            h.headers.get("location", "").startswith("https")
    except Exception as e:
        rep.error = str(e)
    return rep
