"""Static TLD price catalog (typical USD/yr). Used only when live API unavailable.
Values are estimates — always labeled with src=catalog."""

# registrar -> tld -> (register, renew, transfer)
CATALOG: dict[str, dict[str, tuple[float, float, float]]] = {
    "porkbun": {
        "com": (9.73, 11.15, 9.73), "net": (10.88, 12.88, 10.88), "org": (8.55, 10.28, 8.55),
        "io": (33.98, 45.98, 33.98), "dev": (11.99, 13.99, 11.99), "ai": (68.99, 68.99, 68.99),
        "app": (13.99, 14.99, 13.99), "me": (8.99, 14.99, 8.99),
    },
    "cloudflare": {
        "com": (9.77, 9.77, 9.77), "net": (11.05, 11.05, 11.05), "org": (9.93, 9.93, 9.93),
        "io": (34.18, 34.18, 34.18), "dev": (10.11, 10.11, 10.11), "ai": (69.0, 69.0, 69.0),
        "app": (14.0, 14.0, 14.0),
    },
    "namecheap": {
        "com": (13.98, 15.98, 13.98), "net": (12.98, 15.98, 12.98), "org": (8.48, 13.98, 8.48),
        "io": (32.88, 44.88, 32.88), "dev": (12.98, 13.98, 12.98), "ai": (68.98, 68.98, 68.98),
        "app": (14.48, 14.98, 14.48),
    },
    "godaddy": {
        "com": (11.99, 19.99, 11.99), "net": (12.99, 19.99, 12.99), "org": (9.99, 20.99, 9.99),
        "io": (39.99, 59.99, 39.99), "dev": (15.99, 19.99, 15.99), "ai": (69.99, 89.99, 69.99),
        "app": (16.99, 18.99, 16.99),
    },
    "dynadot": {
        "com": (9.49, 10.49, 9.49), "net": (10.49, 12.49, 10.49), "org": (8.99, 11.49, 8.99),
        "io": (32.99, 42.99, 32.99), "dev": (10.99, 12.99, 10.99), "ai": (65.99, 65.99, 65.99),
        "app": (13.49, 14.49, 13.49),
    },
}


def catalog_price(registrar: str, tld: str):
    return CATALOG.get(registrar, {}).get(tld.lower().lstrip("."))
