from __future__ import annotations

import os

from .multi import (CloudflareProvider, DynadotProvider, GoDaddyOfferProvider,
                    NamecheapProvider, PorkbunProvider)


def all_providers() -> list:
    return [
        PorkbunProvider(os.environ.get("PORKBUN_API_KEY"), os.environ.get("PORKBUN_SECRET_KEY")),
        CloudflareProvider(os.environ.get("CLOUDFLARE_API_TOKEN"), os.environ.get("CLOUDFLARE_ACCOUNT_ID")),
        NamecheapProvider(os.environ.get("NAMECHEAP_API_KEY")),
        GoDaddyOfferProvider(),
        DynadotProvider(os.environ.get("DYNADOT_API_KEY")),
    ]


def compare(domain: str) -> list:
    offers = []
    for p in all_providers():
        try:
            offers.append(p.offer(domain))
        except Exception as e:
            from .offer import DomainOffer
            offers.append(DomainOffer(domain=domain, registrar=p.name, error=str(e)))
    return offers
