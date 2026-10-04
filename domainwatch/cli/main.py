from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
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
    from ..core.score import score_domain
    ranked = []
    for c in sorted(candidates):
        st = eng.check_one(c, args.target)
        mark = "AVAILABLE" if st.available else (st.error or "taken")
        price = f" ${st.price:,.2f}" if st.price else ""
        s = score_domain(c, st.available, st.price, st.premium)
        ranked.append((s.total, c, mark, price))
        time.sleep(0.5)
    for total, c, mark, price in sorted(ranked, reverse=True):
        print(f"{c:<35} {mark}{price}   score {total}")
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


def cmd_db(args) -> int:
    from ..storage import migrate
    db = DB()
    if args.action == "migrate":
        applied = migrate.migrate(db.conn)
        print(f"Applied migrations: {applied or 'none (up to date)'}")
    elif args.action == "status":
        s = migrate.status(db.conn)
        print(f"Schema version: {s['current_version']}")
        print(f"Available: {', '.join(s['available_migrations'])}")
    else:
        return cmd_backup(args)
    return 0


def cmd_providers(args) -> int:
    eng = _engine(args)
    print("Running live probes…")
    eng.providers.check("example.com")
    for name, h in eng.providers.health().items():
        st = eng.providers.stats()[name]
        print(f"{name:<12} {h:<10} ok={st['ok']} fail={st['fail']} avg={st['avg_ms']:.0f}ms {st['last_error'] or ''}")
    return 0


def cmd_watch(args) -> int:
    from ..core.lifecycle import classify, days_until
    db = DB()
    for d in args.domains:
        db.add_domain(d)
    eng = _engine(args)
    interval = args.interval
    print(f"DomainWatch v{__version__} — watching…\n")
    while True:
        states = eng.check_all()
        print(f"\n{datetime.now():%H:%M:%S} sweep:")
        for st in states:
            lc = classify(st.available, st.expiration, st.status)
            if st.error:
                print(f"✗ {st.domain:<28} {st.error}")
            elif st.available:
                price = f"${st.price:,.2f}" if st.price else "?"
                print(f"★ {st.domain:<28} AVAILABLE  {price}")
            else:
                days = days_until(st.expiration)
                warn = f" ⚠ expires in {days:.0f}d" if days is not None and days <= 30 else ""
                price = f"${st.price:,.2f}" if st.price else ""
                print(f"✓ {st.domain:<28} {lc.value:<12} {price}{warn}")
        print(f"Next sweep in {interval}s\n")
        time.sleep(interval)


def cmd_doctor(args) -> int:
    import shutil, socket, sqlite3, subprocess
    from ..rdap import client as r
    ok = lambda b: "✓" if b else "✗"
    print("DomainWatch Doctor\n")
    print(f"{ok(True)} Python {sys.version.split()[0]}")
    try:
        load_config(args.config); print(f"{ok(True)} Configuration")
    except Exception as e:
        print(f"✗ Configuration: {e}")
    try:
        db = DB(); db.conn.execute("SELECT 1"); print(f"{ok(True)} SQLite database ({db.path})")
    except Exception as e:
        print(f"✗ SQLite: {e}")
    try:
        socket.gethostbyname("example.com"); print(f"{ok(True)} DNS resolver")
    except Exception:
        print("✗ DNS resolver")
    try:
        r.rdap_lookup("example.com"); print(f"{ok(True)} RDAP connectivity")
    except Exception as e:
        print(f"✗ RDAP: {e}")
    gd = shutil.which("gddy")
    print(f"{ok(bool(gd))} GoDaddy CLI {gd or '(missing)'}")
    if gd:
        p = subprocess.run(["gddy", "auth", "status"], capture_output=True, text=True, timeout=10)
        expired = '"expired": true' in p.stdout
        print(f"{ok(not expired)} GoDaddy auth {'(expired)' if expired else '(ok)'}")
    cfg = load_config(args.config)
    tel = get(cfg, "notifications", "telegram", "enabled", default=False)
    print(f"{ok(False) if tel else ok(True)} Telegram config {'enabled' if tel else 'not configured'}")
    print(f"\nLog: ~/.domainwatch/domainwatch.db")
    return 0


def _export_rows():
    db = DB()
    return [dict(r) for r in db.list_domains()]


def cmd_export(args) -> int:
    import csv, json, yaml as y
    rows = _export_rows()
    fmt = args.format
    out = args.output or f"domains.{fmt if fmt != 'yaml' else 'yml'}"
    if fmt == "json":
        Path(out).write_text(json.dumps(rows, indent=2, default=str))
    elif fmt == "csv":
        with open(out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys() if rows else ["domain"])
            w.writeheader(); w.writerows(rows)
    else:
        Path(out).write_text(y.safe_dump(rows))
    print(f"Exported {len(rows)} domains to {out}")
    return 0


def cmd_import(args) -> int:
    import json, yaml as y
    data = y.safe_load(Path(args.file).read_text()) if args.file.endswith((".yml", ".yaml")) else json.loads(Path(args.file).read_text())
    db = DB()
    for d in data:
        if isinstance(d, dict):
            db.add_domain(d["domain"], d.get("target_price"))
        else:
            db.add_domain(str(d))
    print(f"Imported {len(data)} domains")
    return 0


def cmd_backup(args) -> int:
    import shutil
    from datetime import datetime as dt
    db = DB()
    out = args.output or f"domainwatch-{dt.now():%Y-%m-%d}.db"
    shutil.copy2(db.path, out)
    print(f"Backup written to {out}")
    return 0


def cmd_tls(args) -> int:
    from ..security import tls
    i = tls.inspect(args.domain)
    if not i.ok:
        print(f"TLS error: {i.error}"); return 1
    print(f"Subject: {i.subject}\nIssuer: {i.issuer}\nVersion: {i.version}\n"
          f"Valid: {i.not_before} → {i.not_after} ({i.days_remaining:.0f} days left)\n"
          f"SANs: {', '.join(i.sans[:5])}")
    if i.days_remaining is not None and i.days_remaining < 14:
        print(f"⚠ certificate expires in {i.days_remaining:.0f} days")
    return 0


def cmd_http(args) -> int:
    from ..security import httpmon
    r = httpmon.check(args.domain)
    if not r.ok:
        print(f"HTTP error: {r.error}"); return 1
    print(f"Status: {r.status}  {r.elapsed_ms:.0f}ms\nHTTPS redirect: {r.https_redirect}")
    present = [h for h in r.headers if h in r.headers]
    for h in ("strict-transport-security", "content-security-policy", "x-content-type-options", "x-frame-options", "referrer-policy"):
        print(f"  {h:<30} {'✓' if h in r.headers else '✗ MISSING'}")
    return 0


def cmd_score(args) -> int:
    from ..core.score import score_domain
    from ..config import load_config, get
    cfg = load_config(args.config)
    weights = get(cfg, "scoring", "weights", default=None)
    eng = _engine(args)
    st = eng.check_one(args.domain, None)
    created = None
    try:
        info = rdap_client.parse_rdap(rdap_client.rdap_lookup(args.domain).get("raw") or {})
        created = info.get("created")
    except Exception:
        pass
    res = score_domain(args.domain, st.available, st.price, st.premium,
                       created=created, status=st.status, weights=weights)
    print(res.render())
    return 0


def cmd_price_compare(args) -> int:
    from ..providers import registry
    offers = registry.compare(args.domain)
    print(f"\n{'Registrar':<14} {'Register':>10} {'Renew':>10} {'Transfer':>10} {'Avail':>6} {'Src':>8}")
    print("-" * 64)
    for o in offers:
        if o.error:
            print(f"{o.registrar:<14} ERROR: {o.error[:40]}")
            continue
        row = o.as_row()
        print(f"{row['Registrar']:<14} {row['Register']:>10} {row['Renew']:>10} {row['Transfer']:>10} {row['Avail']:>6} {row['Src']:>8}")
    print("\nSrc: live = live API/CLI price, catalog = estimated TLD list")
    return 0


def cmd_lifecycle(args) -> int:
    from ..core.lifecycle import classify, days_until
    db = DB()
    last = db.last_check(args.domain)
    if last:
        lc = classify(bool(last["available"]) if last["available"] is not None else None, last["expiration"], last["status"])
        print(f"{args.domain}: {lc.value} (expires {last['expiration'] or 'unknown'})")
    else:
        info = rdap_client.parse_rdap(rdap_client.rdap_lookup(args.domain).get("raw") or {})
        lc = classify(info.get("available"), info.get("expiration"))
        print(f"{args.domain}: {lc.value} (expires {info.get('expiration','unknown')})")
    return 0


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
    s = sub.add_parser("db"); s.add_argument("action", choices=["migrate", "status", "backup"]); s.add_argument("--output"); s.set_defaults(func=cmd_db)
    sub.add_parser("providers").set_defaults(func=cmd_providers)
    s = sub.add_parser("watch"); s.add_argument("domains", nargs="*"); s.add_argument("-i", "--interval", type=float, default=300); s.add_argument("-v", "--verbose", action="store_true"); s.set_defaults(func=cmd_watch)
    sub.add_parser("doctor").set_defaults(func=cmd_doctor)
    s = sub.add_parser("export"); s.add_argument("output", nargs="?"); s.add_argument("--format", choices=["json", "csv", "yaml"], default="json"); s.set_defaults(func=cmd_export)
    s = sub.add_parser("import"); s.add_argument("file"); s.set_defaults(func=cmd_import)
    s = sub.add_parser("backup"); s.add_argument("--output"); s.set_defaults(func=cmd_backup)
    s = sub.add_parser("tls"); s.add_argument("domain"); s.set_defaults(func=cmd_tls)
    s = sub.add_parser("http"); s.add_argument("domain"); s.set_defaults(func=cmd_http)
    s = sub.add_parser("lifecycle"); s.add_argument("domain"); s.set_defaults(func=cmd_lifecycle)
    s = sub.add_parser("price-compare"); s.add_argument("domain"); s.set_defaults(func=cmd_price_compare)
    s = sub.add_parser("score"); s.add_argument("domain"); s.set_defaults(func=cmd_score)
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
