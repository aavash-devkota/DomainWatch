from __future__ import annotations

import abc
from typing import Optional

from ..core.models import DomainState


class Provider(abc.ABC):
    name = "base"

    @abc.abstractmethod
    def check(self, domain: str) -> DomainState:
        """Return a DomainState for the domain."""

    def available(self, domain: str) -> Optional[bool]:
        return self.check(domain).available

    def price(self, domain: str) -> Optional[float]:
        return self.check(domain).price
