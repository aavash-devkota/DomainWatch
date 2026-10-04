"""RDAP-backed availability fallback (no API key needed)."""
from __future__ import annotations

import re
from typing import Any, Optional

import requests

from ..core.models import DomainState
from .base import Provider

RDAP_BOOTSTRAP = "https://data.iana.org/rdap/dns.json"
_cache: dict[str, str] = {}


def _rdap_base(tld: str) -> Optional[str]:
    if tld in _cache:
        return _cache[tld]
    try:
        data = requests.get(RDAP_BOOTSTRAP, timeout=10).json()
        for service_tlds, urls in data.get("services", []):
            for t in service_tlds:
                if t not in _cache and urls:
                    _cache[t] = urls[0].rstrip("/")
    except Exception:
        pass
    return _cache.get(tld)


def rdap_lookup(domain: str) -> dict[str, Any]:
    tld = domain.rsplit(".", 1)[-1].lower()
    base = _rdap_base(tld) or "https://rdap.org"
    r = requests.get(f"{base}/domain/{domain}", timeout=15,
                     headers={"Accept": "application/rdap+json"})
    if r.status_code == 404:
        return {"available": True, "raw": None}
    r.raise_for_status()
    raw = r.json()
    return {"available": False, "raw": raw}


def parse_rdap(raw: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for ev in raw.get("events", []):
        a = ev.get("eventAction")
        if a == "registration":
            out["created"] = ev.get("eventDate")
        elif a == "expiration":
            out["expiration"] = ev.get("eventDate")
        elif a == "last changed":
            out["updated"] = ev.get("eventDate")
    for ent in raw.get("entities", []):
        roles = ent.get("roles", [])
        if "registrar" in roles:
            v = ent.get("vcardArray")
            if v and len(v) == 2:
                for item in v[1]:
                    if item[0] == "fn":
                        out["registrar"] = item[3]
    out["nameservers"] = [ns.get("ldhName") for ns in raw.get("nameservers", []) if ns.get("ldhName")]
    out["status"] = raw.get("status", [])
    return out


class RdapProvider(Provider):
    name = "rdap"

    def check(self, domain: str) -> DomainState:
        state = DomainState(domain=domain, provider=self.name)
        try:
            res = rdap_lookup(domain)
        except Exception as e:
            state.error = str(e)
            return state
        state.available = res["available"]
        if res["raw"]:
            info = parse_rdap(res["raw"])
            state.expiration = info.get("expiration")
            state.registrar = info.get("registrar")
            state.nameservers = info.get("nameservers", [])
            state.status = ", ".join(info.get("status", [])) or None
        return state
