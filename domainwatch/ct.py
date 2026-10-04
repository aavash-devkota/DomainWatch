from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import requests

CRTSH = "https://crt.sh/?q=%25.{domain}&output=json"


@dataclass
class CTEntry:
    domain: str
    name_value: str       # SANs (newline separated in source)
    issuer: str
    not_before: str
    cert_id: str

    def sans(self) -> list[str]:
        return [s.strip() for s in self.name_value.split("\n") if s.strip()]


def fetch(domain: str, limit: int = 50) -> list[CTEntry]:
    url = f"https://crt.sh/?q=%25.{domain}&output=json"
    out = []
    import time as _t
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0 DomainWatch"})
            r.raise_for_status()
            data = r.json()
            for row in data[: limit * 4]:
                out.append(CTEntry(
                    domain=domain,
                    name_value=row.get("name_value", ""),
                    issuer=row.get("issuer_name", ""),
                    not_before=row.get("not_before", ""),
                    cert_id=str(row.get("id", "")),
                ))
            break
        except Exception:
            _t.sleep(2 * (attempt + 1))
    if not out:
        out = _certspotter(domain, limit)
    # empty is a valid result (no CT entries); error only if both sources failed
    # dedupe by cert id, keep newest first
    seen, uniq = set(), []
    for e in sorted(out, key=lambda e: e.not_before, reverse=True):
        if e.cert_id in seen:
            continue
        seen.add(e.cert_id)
        uniq.append(e)
        if len(uniq) >= limit:
            break
    return uniq


def _certspotter(domain: str, limit: int = 50) -> list[CTEntry]:
    try:
        r = requests.get(
            f"https://api.certspotter.com/v1/issuances?domain={domain}&include_subdomains=true&expand=dns_names",
            timeout=20, headers={"User-Agent": "DomainWatch"})
        r.raise_for_status()
        out = []
        for row in r.json()[:limit]:
            iss = row.get("issuer") or {}
            issuer = iss.get("name", "") or row.get("issuer_name", "") or iss.get("slug", "") or iss.get("url", "")
            out.append(CTEntry(
                domain=domain,
                name_value="\n".join(row.get("dns_names", [])),
                issuer=issuer,
                not_before=row.get("not_before", ""),
                cert_id=row.get("id", ""),
            ))
        return out
    except Exception:
        return []


def subdomains(domain: str, limit: int = 200) -> list[str]:
    subs: set[str] = set()
    try:
        for e in fetch(domain, limit=limit):
            for san in e.sans():
                san = san.lstrip("*.").strip()
                if san.endswith("." + domain) and "*" not in san:
                    subs.add(san)
    except Exception:
        pass
    return sorted(subs)
