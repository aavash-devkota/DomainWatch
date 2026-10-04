from __future__ import annotations

import dns.resolver
import dns.rdatatype

RECORD_TYPES = ["A", "AAAA", "MX", "NS", "CNAME", "TXT", "CAA", "SOA"]


def lookup(domain: str, types=None) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for t in (types or RECORD_TYPES):
        try:
            answers = dns.resolver.resolve(domain, t, lifetime=8)
            out[t] = sorted({r.to_text().strip('"') for r in answers})
        except Exception:
            out[t] = []
    return out


def txt_values(domain: str) -> list[str]:
    return lookup(domain, ["TXT"]).get("TXT", [])


def has_dnssec(domain: str) -> bool:
    try:
        answers = dns.resolver.resolve(domain, "DNSKEY", lifetime=8)
        return len(answers) > 0
    except Exception:
        try:
            answers = dns.resolver.resolve(domain, "DS", lifetime=8)
            return len(answers) > 0
        except Exception:
            return False


def spf_record(domain: str):
    for v in txt_values(domain):
        if v.startswith("v=spf1"):
            return v
    return None


def dmarc_record(domain: str):
    vals = lookup(f"_dmarc.{domain}", ["TXT"]).get("TXT", [])
    for v in vals:
        if v.startswith("v=DMARC1"):
            return v
    return None


def caa_records(domain: str) -> list[str]:
    return lookup(domain, ["CAA"]).get("CAA", [])
