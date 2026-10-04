from __future__ import annotations

import random
import time


class AdaptiveInterval:
    """Backoff with jitter: normal interval -> doubles up to max on errors, halves on success."""

    def __init__(self, base: float = 300, max_interval: float = 3600):
        self.base = base
        self.current = base
        self.max_interval = max_interval

    def success(self) -> float:
        self.current = max(self.base, self.current / 2)
        return self.sleep()

    def failure(self) -> float:
        self.current = min(self.max_interval, self.current * 2)
        return self.sleep()

    def sleep(self) -> float:
        jitter = random.uniform(0.85, 1.15)
        return self.current * jitter

    def wait(self, ok: bool) -> None:
        secs = self.success() if ok else self.failure()
        time.sleep(secs)
