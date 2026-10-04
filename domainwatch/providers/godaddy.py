"""GoDaddy provider backed by the `gddy` CLI."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from typing import Any, Optional

from ..core.models import DomainState
from .base import Provider


def _run(args: list[str], timeout: int = 45) -> dict[str, Any]:
    if shutil.which("gddy") is None:
        raise RuntimeError("gddy CLI not installed")
    try:
        proc = subprocess.run(
            ["gddy", *args, "-o", "json", "--timeout", "30s"],
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError("gddy timed out") from e
    out = (proc.stdout or "") + (proc.stderr or "")
    if "Opening browser" in out:
        raise RuntimeError("gddy needs auth — run `gddy auth login`")
    if proc.returncode != 0:
        raise RuntimeError(out.strip().splitlines()[0] if out.strip() else f"gddy exit {proc.returncode}")
    data = json.loads(proc.stdout)
    if isinstance(data, dict) and "data" in data:
        data = data["data"]
    if isinstance(data, list):
        data = data[0] if data else {}
    return data


def _price(v) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    m = re.search(r"[\d,]+(?:\.\d+)?", str(v))
    return float(m.group(0).replace(",", "")) if m else None


class GoDaddyProvider(Provider):
    name = "godaddy"

    def check(self, domain: str) -> DomainState:
        state = DomainState(domain=domain, provider=self.name)
        try:
            avail = _run(["domain", "available", domain])
        except (RuntimeError, json.JSONDecodeError) as e:
            state.error = str(e)
            return state
        state.available = bool(avail.get("available"))
        state.definitive = avail.get("definitive")
        state.currency = avail.get("currency") or "USD"
        inv = (avail.get("inventory") or "").lower()
        state.premium = any(k in inv for k in ("premium", "aftermarket", "auction"))
        if state.available:
            try:
                quote = _run(["domain", "quote", domain])
                state.price = _price(quote.get("price"))
                state.renewal_price = _price(quote.get("renewalPrice"))
                state.currency = quote.get("currency") or state.currency
                inv = (quote.get("inventory") or inv).lower()
                state.premium = any(k in inv for k in ("premium", "aftermarket", "auction"))
            except (RuntimeError, json.JSONDecodeError):
                terms = avail.get("terms") or []
                if terms and isinstance(terms[0], dict):
                    state.price = _price(terms[0].get("price"))
        return state
