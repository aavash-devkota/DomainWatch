from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

DEFAULT_WEIGHTS = {
    "availability": 20,
    "price": 20,
    "tld": 20,
    "brandability": 20,
    "history": 10,
    "risk": 10,
}

TLD_SCORES = {
    "com": 1.0, "net": 0.75, "org": 0.75, "io": 0.9, "dev": 0.9,
    "ai": 0.85, "app": 0.85, "co": 0.7, "tools": 0.7, "devs": 0.6,
}

HIGH_RISK_HINTS = ("login", "secure-", "pay-", "verify", "wallet", "bank", "free-")


@dataclass
class ScoreResult:
    domain: str
    total: int
    parts: dict[str, float] = field(default_factory=dict)
    details: dict[str, str] = field(default_factory=dict)

    def render(self) -> str:
        lines = [f"Domain Opportunity Score: {self.total}/100\n"]
        maxes = DEFAULT_WEIGHTS
        for name, pts in self.parts.items():
            lines.append(f"{name.capitalize():<18} {pts:>5.1f}/{maxes[name]}   {self.details.get(name, '')}")
        lines.append("-" * 45)
        lines.append(f"{'Total':<18} {self.total:>5}/100")
        return "\n".join(lines)


def _tld(domain: str) -> str:
    return domain.rsplit(".", 1)[-1].lower()


def brandability(name: str) -> tuple[float, str]:
    score = 1.0
    reasons = []
    base = name.split(".")[0]
    if len(base) <= 5:
        pass
    elif len(base) <= 9:
        score -= 0.1
    elif len(base) <= 14:
        score -= 0.3
        reasons.append("long")
    else:
        score -= 0.5
        reasons.append("very long")
    if "-" in base:
        score -= 0.25
        reasons.append("hyphen")
    if any(c.isdigit() for c in base):
        score -= 0.15
        reasons.append("digits")
    vowels = sum(1 for c in base if c in "aeiou")
    if base and vowels / len(base) < 0.2:
        score -= 0.15
        reasons.append("hard to pronounce")
    return max(0.0, min(1.0, score)), ", ".join(reasons) or "good shape"


def score_domain(domain: str, available: Optional[bool], price: Optional[float],
                 premium: Optional[bool], tld_score: Optional[float] = None,
                 created: Optional[str] = None, status: Optional[str] = None,
                 weights: Optional[dict] = None) -> ScoreResult:
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    parts: dict[str, float] = {}
    details: dict[str, str] = {}

    # availability
    if available is True:
        parts["availability"] = w["availability"]
        details["availability"] = "available now"
    elif available is False:
        parts["availability"] = 0
        details["availability"] = "taken"
    else:
        parts["availability"] = w["availability"] * 0.5
        details["availability"] = "unknown"

    # price
    if price is None:
        parts["price"] = w["price"] * 0.5
        details["price"] = "unknown"
    elif price <= 10:
        parts["price"] = w["price"]
        details["price"] = f"${price:.2f} — great"
    elif price <= 20:
        parts["price"] = w["price"] * 0.8
        details["price"] = f"${price:.2f} — fair"
    elif price <= 50:
        parts["price"] = w["price"] * 0.5
        details["price"] = f"${price:.2f} — pricey"
    else:
        parts["price"] = w["price"] * 0.2
        details["price"] = f"${price:.2f} — premium"

    # tld quality
    t = _tld(domain)
    ts = TLD_SCORES.get(t, 0.5)
    parts["tld"] = w["tld"] * ts
    details["tld"] = f".{t}"

    # brandability
    b, why = brandability(domain)
    parts["brandability"] = w["brandability"] * b
    details["brandability"] = why

    # history
    if created:
        from datetime import datetime, timezone
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            age_days = (datetime.now(timezone.utc) - dt).days
            years = age_days / 365
            parts["history"] = w["history"] * min(1.0, years / 5)
            details["history"] = f"~{years:.1f}y old"
        except ValueError:
            parts["history"] = w["history"] * 0.5
            details["history"] = "unparseable"
    elif available is False:
        parts["history"] = w["history"] * 0.6
        details["history"] = "registered (unknown age)"
    else:
        parts["history"] = w["history"] * 0.3
        details["history"] = "no history (fresh)"

    # risk
    risk = 1.0
    if premium:
        risk -= 0.6
        details["risk"] = "premium/aftermarket"
    base = domain.split(".")[0].lower()
    if any(h in base for h in HIGH_RISK_HINTS):
        risk -= 0.3
        details["risk"] = (details.get("risk", "") + ", typo-squatting hint").strip(", ")
    parts["risk"] = w["risk"] * max(0.0, risk)
    if "risk" not in details:
        details["risk"] = "low" if risk >= 0.8 else "elevated"

    total = int(sum(parts.values()))
    return ScoreResult(domain=domain, total=total, parts=parts, details=details)
