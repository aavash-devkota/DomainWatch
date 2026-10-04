from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .. import __version__
from ..config import load_config, get
from ..core.engine import Engine
from ..dns import records
from ..notifications.base import build_notifiers
from ..rdap import client as rdap_client
from ..scheduler.adaptive import AdaptiveInterval
from ..security import audit as audit_mod
from ..storage.db import DB


def _engine(args) -> Engine:
    cfg = load_config(getattr(args, "config", None))
    db = DB()
    eng = Engine(db=db)
    for n in build_notifiers(cfg):
        eng.bus.subscribe_all(n.send)
    return eng


def cmd_check(args) -> int:
    eng = _engine(args)
    targets = list(args.domains)
    if args.file:
        for line in Path(args.file).read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                targets.append(line)
    for d in targets:
        d = d.strip()
        if not d:
            continue
        st = eng.check_one(d, args.target)
        if st.error:
            print(f"[x] {d}: {st.error}")
        elif st.available:
            p = f"${st.price:,.2f}" if st.price is not None else "price n/a"
            prem = " [PREMIUM]" if st.premium else ""
            print(f"[+] {d}: AVAILABLE — {p} {st.currency}/yr{prem} (via {st.provider})")
        else:
            print(f"[x] {d}: TAKEN (registrar: {st.registrar or 'n/a'}, expires: {st.expiration or 'n/a'})")
    return 0


def cmd_add(args) -> int:
    db = DB()
    for d in args.domains:
        db.add_domain(d, args.target)
        print(f"added {d}")
    return 0


def cmd_remove(args) -> int:
    db = DB()
    for d in args.domains:
        db.remove_domain(d)
        print(f"removed {d}")
    return 0


def cmd_list(args) -> int:
    db = DB()
    rows = db.list_domains()
    if not rows:
        print("No domains tracked. Use: domain-monitor add <domain>")
        return 0
    for r in rows:
        print(f"{r['domain']:<30} target=${r['target_price'] if r['target_price'] is not None else '-'}  enabled={bool(r['enabled'])}")
    return 0


def cmd_status(args) -> int:
    db = DB()
    for r in db.list_domains():
        last = db.last_check(r["domain"])
        if not last:
            print(f"{r['domain']}: never checked")
            continue
        avail = "AVAILABLE" if last["available"] else ("taken" if last["available"] == 0 else "?")
        price = f"${last['price']:,.2f}" if last["price"] is not None else "-"
        print(f"{r['domain']:<30} {avail:<10} {price:<10} expires {last['expiration'] or '-'}  ({last['timestamp']})")
    return 0


def cmd_history(args) -> int:
    db = DB()
    rows = db.history(args.domain)
    if not rows:
        print("No history.")
        return 0
    for r in rows:
        avail = "avail" if r["available"] else ("taken" if r["available"] == 0 else "err")
        price = f"${r['price']:,.2f}" if r["price"] is not None else "-"
        print(f"{r['timestamp']}  {avail:<6} {price:<10} {r['provider'] or '-'} {r['error'] or ''}")
    return 0


def cmd_price(args) -> int:
    db = DB()
    stats = db.price_stats(args.domain)
    if not stats:
        print("No price data yet.")
        return 0
    print(f"{args.domain}: lowest ${stats['lowest']:.2f} | highest ${stats['highest']:.2f} | "
          f"current ${stats['current']:.2f} | avg ${stats['average']:.2f} | {stats['samples']} samples")
    return 0


def cmd_expiration(args) -> int:
    db = DB()
    last = db.last_check(args.domain)
    if last and last["expiration"]:
        print(f"{args.domain} expires: {last['expiration']}")
        return 0
    # live fallback
    info = rdap_client.parse_rdap(rdap_client.rdap_lookup(args.domain).get("raw") or {})
    print(f"{args.domain} expires: {info.get('expiration', 'unknown')}")
    return 0


def cmd_timeline(args) -> int:
    db = DB()
    for r in db.events(args.domain or None, limit=100):
        print(f"{r['timestamp']}  {r['type']:<22} {r['message']}")
    return 0


def cmd_rdap(args) -> int:
    res = rdap_client.rdap_lookup(args.domain)
    if res["available"]:
        print(f"{args.domain}: NOT REGISTERED (RDAP 404)")
        return 0
    info = rdap_client.parse_rdap(res["raw"])
    print(f"Domain:      {args.domain}")
    print(f"Registrar:  {info.get('registrar', '-')}")
    print(f"Created:    {info.get('created', '-')}")
    print(f"Updated:    {info.get('updated', '-')}")
    print(f"Expires:    {info.get('expiration', '-')}")
    print(f"Status:     {', '.join(info.get('status', []))}")
    print(f"Nameservers: {', '.join(info.get('nameservers', []))}")
    return 0


def cmd_dns(args) -> int:
    data = records.lookup(args.domain)
    for t, vals in data.items():
        if vals:
            print(f"{t:<6} {', '.join(vals)}")
    return 0


def cmd_audit(args) -> int:
    print(audit_mod.render(audit_mod.audit(args.domain)))
    return 0


def cmd_discover(args) -> int:
    base = args.name
    tlds = args.tlds or ["com", "net", "org", "io", "dev", "ai", "app"]
    prefixes = args.prefixes or ["get", "try", "my", "the"]
    suffixes = args.suffixes or ["app", "hq", "labs", "io", "ly"]
    candidates = {f"{base}.{t}" for t in tlds}
    candidates |= {f"{p}{base}.com" for p in prefixes}
    candidates |= {f"{base}{s}.com" for s in suffixes}
    eng = _engine(args)
    for c in sorted(candidates):
        st = eng.check_one(c, args.target)
        mark = "AVAILABLE" if st.available else (st.error or "taken")
        price = f" ${st.price:,.2f}" if st.price else ""
        print(f"{c:<35} {mark}{price}")
        time.sleep(0.5)
    return 0


def cmd_run(args) -> int:
    cfg = load_config(args.config)
    eng = _engine(args)
    # seed domains from config
    for d in get(cfg, "domains", default=[]) or []:
        if isinstance(d, dict):
            eng.db.add_domain(d["domain"], d.get("target_price"))
        else:
            eng.db.add_domain(str(d))
    interval = args.interval or get(cfg, "monitor", "interval", default=300)
    adaptive = AdaptiveInterval(base=float(interval))
    print(f"Monitoring every ~{interval}s (adaptive backoff on errors). Ctrl+C to stop.")
    while True:
        ok = True
        for st in eng.check_all():
            if st.error:
                ok = False
                print(f"[x] {st.domain}: {st.error}")
            elif st.available:
                price = f"${st.price:,.2f}" if st.price is not None else "?"
                print(f"[+] {st.domain}: AVAILABLE {price}")
            else:
                print(f"[x] {st.domain}: taken")
        adaptive.wait(ok)


def cmd_monitor(args) -> int:
    db = DB()
    for d in args.domains:
        db.add_domain(d)
    return cmd_run(args)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="domain-monitor", description="DomainWatch CLI")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("-c", "--config", help="path to config.yaml", default=None)
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("check"); s.add_argument("domains", nargs="*"); s.add_argument("-f", "--file"); s.add_argument("-t", "--target", type=float); s.set_defaults(func=cmd_check)
    s = sub.add_parser("add"); s.add_argument("domains", nargs="+"); s.add_argument("-t", "--target", type=float); s.set_defaults(func=cmd_add)
    s = sub.add_parser("remove"); s.add_argument("domains", nargs="+"); s.set_defaults(func=cmd_remove)
    sub.add_parser("list").set_defaults(func=cmd_list)
    sub.add_parser("status").set_defaults(func=cmd_status)
    s = sub.add_parser("history"); s.add_argument("domain"); s.set_defaults(func=cmd_history)
    s = sub.add_parser("price"); s.add_argument("domain"); s.set_defaults(func=cmd_price)
    s = sub.add_parser("expiration"); s.add_argument("domain"); s.set_defaults(func=cmd_expiration)
    s = sub.add_parser("timeline"); s.add_argument("domain", nargs="?"); s.set_defaults(func=cmd_timeline)
    s = sub.add_parser("rdap"); s.add_argument("domain"); s.set_defaults(func=cmd_rdap)
    s = sub.add_parser("dns"); s.add_argument("domain"); s.set_defaults(func=cmd_dns)
    s = sub.add_parser("audit"); s.add_argument("domain"); s.set_defaults(func=cmd_audit)
    s = sub.add_parser("discover"); s.add_argument("name"); s.add_argument("--tlds", nargs="*"); s.add_argument("--prefixes", nargs="*"); s.add_argument("--suffixes", nargs="*"); s.add_argument("-t", "--target", type=float); s.set_defaults(func=cmd_discover)
    s = sub.add_parser("run"); s.add_argument("-i", "--interval", type=float); s.set_defaults(func=cmd_run)
    s = sub.add_parser("monitor"); s.add_argument("domains", nargs="*"); s.add_argument("-i", "--interval", type=float, default=300); s.set_defaults(func=cmd_monitor)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nStopped.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
