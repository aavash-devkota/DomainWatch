from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DomainOffer:
    domain: str
    registrar: str
    available: Optional[bool] = None
    registration_price: Optional[float] = None
    renewal_price: Optional[float] = None
    transfer_price: Optional[float] = None
    currency: str = "USD"
    premium: bool = False
    source: str = "live"          # "live" or "catalog" (estimated)
    error: Optional[str] = None

    def as_row(self) -> dict:
        return {
            "Registrar": self.registrar,
            "Register": f"${self.registration_price:,.2f}" if self.registration_price is not None else "-",
            "Renew": f"${self.renewal_price:,.2f}" if self.renewal_price is not None else "-",
            "Transfer": f"${self.transfer_price:,.2f}" if self.transfer_price is not None else "-",
            "Avail": "yes" if self.available else ("no" if self.available is False else "?"),
            "Src": self.source,
        }
