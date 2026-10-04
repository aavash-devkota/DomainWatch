from __future__ import annotations

import time
from collections import Counter
from typing import Optional

from ..core.models import DomainState
from .base import Provider


class ProviderManager:
    """Tries providers in priority order; falls back on failure; tracks health."""

    def __init__(self, providers: list[Provider]):
        self.providers = providers
        self._ok: Counter = Counter()
        self._fail: Counter = Counter()
        self._last_error: dict[str, str] = {}
        self._latencies: dict[str, list[float]] = {}

    def check(self, domain: str) -> DomainState:
        last_err: Optional[str] = None
        for p in self.providers:
            t0 = time.monotonic()
            try:
                state = p.check(domain)
            except Exception as e:
                self._fail[p.name] += 1
                self._last_error[p.name] = str(e)
                last_err = str(e)
                continue
            dt = (time.monotonic() - t0) * 1000
            self._latencies.setdefault(p.name, []).append(dt)
            if state.error:
                self._fail[p.name] += 1
                self._last_error[p.name] = state.error
                last_err = state.error
                continue
            self._ok[p.name] += 1
            return state
        return DomainState(domain=domain, error=last_err or "all providers failed",
                            provider="none")

    def health(self) -> dict[str, str]:
        out = {}
        for p in self.providers:
            fails = self._fail[p.name]
            oks = self._ok[p.name]
            if fails == 0 and oks > 0:
                out[p.name] = "HEALTHY"
            elif oks == 0 and fails > 0:
                err = self._last_error.get(p.name, "")
                out[p.name] = "OFFLINE" if "timed out" not in err.lower() else "RATE/TIMEOUT"
            elif fails > 0:
                out[p.name] = "DEGRADED"
            else:
                out[p.name] = "UNKNOWN"
        return out

    def stats(self) -> dict[str, dict]:
        return {p.name: {"ok": self._ok[p.name], "fail": self._fail[p.name],
                         "last_error": self._last_error.get(p.name),
                         "avg_ms": (sum(self._latencies.get(p.name, [0])) /
                                    max(len(self._latencies.get(p.name, [1])), 1))}
                for p in self.providers}
