from __future__ import annotations

import re
from typing import Optional

import requests

from .catalog import catalog_price
from .offer import DomainOffer


class NamecheapProvider:
    """Namecheap XML API (needs key); availability via RDAP; price via catalog fallback."""

    name = "namecheap"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def offer(self, domain: str) -> DomainOffer:
        tld = domain.rsplit(".", 1)[-1]
        o = DomainOffer(domain=domain, registrar="Namecheap")
        try:
            from ..providers.rdap_provider import rdap_lookup
            o.available = rdap_lookup(domain)["available"]
        except Exception:
            o.available = None
        live = self._live_price(tld) if self.api_key else None
        if live:
            o.registration_price, o.renewal_price, o.transfer_price = live
            o.source = "live"
        else:
            cat = catalog_price("namecheap", tld)
            if cat:
                o.registration_price, o.renewal_price, o.transfer_price = cat
                o.source = "catalog"
        return o

    def _live_price(self, tld: str):
        return None  # requires paid API key flow


class CloudflareProvider:
    name = "cloudflare"

    def __init__(self, api_token: Optional[str] = None, account_id: Optional[str] = None):
        self.api_token, self.account_id = api_token, account_id

    def offer(self, domain: str) -> DomainOffer:
        tld = domain.rsplit(".", 1)[-1]
        o = DomainOffer(domain=domain, registrar="Cloudflare")
        try:
            from ..providers.rdap_provider import rdap_lookup
            o.available = rdap_lookup(domain)["available"]
        except Exception:
            o.available = None
        live = self._live_price(tld) if self.api_token else None
        if live:
            o.registration_price, o.renewal_price, o.transfer_price = live
        else:
            cat = catalog_price("cloudflare", tld)
            if cat:
                o.registration_price, o.renewal_price, o.transfer_price = cat
                o.source = "catalog"
        return o

    def _live_price(self, tld: str):
        try:
            r = requests.get(
                f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/registrar/domains",
                headers={"Authorization": f"Bearer {self.api_token}"}, timeout=10)
            # limited; fallback to catalog
            return None
        except Exception:
            return None


class PorkbunProvider:
    name = "porkbun"

    def __init__(self, api_key: Optional[str] = None, secret: Optional[str] = None):
        self.api_key, self.secret = api_key, secret

    def offer(self, domain: str) -> DomainOffer:
        tld = domain.rsplit(".", 1)[-1]
        o = DomainOffer(domain=domain, registrar="Porkbun")
        try:
            from ..providers.rdap_provider import rdap_lookup
            o.available = rdap_lookup(domain)["available"]
        except Exception:
            o.available = None
        live = self._live_price(tld)
        if live:
            o.registration_price, o.renewal_price, o.transfer_price = live
        else:
            cat = catalog_price("porkbun", tld)
            if cat:
                o.registration_price, o.renewal_price, o.transfer_price = cat
                o.source = "catalog"
        return o

    def _live_price(self, tld: str):
        try:
            r = requests.post("https://porkbun.com/api/json/v3/pricing/get",
                              json={"apikey": self.api_key or "", "secretapikey": self.secret or ""},
                              timeout=10)
            data = r.json()
            if data.get("status") == "SUCCESS" and tld in data.get("pricing", {}):
                p = data["pricing"][tld]
                return (float(p["registration"]), float(p["renewal"]), float(p["transfer"]))
        except Exception:
            pass
        return None


class DynadotProvider:
    name = "dynadot"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def offer(self, domain: str) -> DomainOffer:
        tld = domain.rsplit(".", 1)[-1]
        o = DomainOffer(domain=domain, registrar="Dynadot")
        try:
            from ..providers.rdap_provider import rdap_lookup
            o.available = rdap_lookup(domain)["available"]
        except Exception:
            o.available = None
        cat = catalog_price("dynadot", tld)
        if cat:
            o.registration_price, o.renewal_price, o.transfer_price = cat
            o.source = "catalog"
        return o


class GoDaddyOfferProvider:
    name = "godaddy"

    def offer(self, domain: str) -> DomainOffer:
        tld = domain.rsplit(".", 1)[-1]
        o = DomainOffer(domain=domain, registrar="GoDaddy")
        try:
            from .godaddy import GoDaddyProvider
            st = GoDaddyProvider().check(domain)
            o.available = st.available
            o.registration_price = st.price
            o.renewal_price = st.renewal_price
            o.currency = st.currency
            o.premium = bool(st.premium)
            if st.error:
                o.error = st.error
            else:
                o.source = "live"
        except Exception as e:
            o.error = str(e)
        if o.registration_price is None:
            cat = catalog_price("godaddy", tld)
            if cat:
                o.registration_price, o.renewal_price, o.transfer_price = cat
                o.source = "catalog"
        return o
