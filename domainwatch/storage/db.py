from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

DEFAULT_DB = Path.home() / ".domainwatch" / "domainwatch.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS domains (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT UNIQUE NOT NULL,
    target_price REAL,
    enabled INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL,
    timestamp TEXT DEFAULT (datetime('now')),
    available INTEGER,
    price REAL,
    renewal_price REAL,
    currency TEXT,
    premium INTEGER,
    provider TEXT,
    expiration TEXT,
    registrar TEXT,
    status TEXT,
    error TEXT
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT (datetime('now')),
    type TEXT,
    domain TEXT,
    message TEXT,
    data TEXT
);
CREATE INDEX IF NOT EXISTS idx_checks_domain ON checks(domain);
CREATE TABLE IF NOT EXISTS dns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL,
    timestamp TEXT DEFAULT (datetime('now')),
    record_type TEXT,
    value TEXT
);
"""


class DB:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else DEFAULT_DB
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        from . import migrate
        migrate.migrate(self.conn)

    def add_domain(self, domain: str, target_price: Optional[float] = None) -> None:
        self.conn.execute(
            "INSERT INTO domains(domain, target_price) VALUES(?, ?) "
            "ON CONFLICT(domain) DO UPDATE SET target_price=excluded.target_price",
            (domain, target_price),
        )
        self.conn.commit()

    def remove_domain(self, domain: str) -> None:
        self.conn.execute("DELETE FROM domains WHERE domain=?", (domain,))
        self.conn.commit()

    def list_domains(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM domains ORDER BY domain").fetchall()

    def record_check(self, state) -> None:
        d = state.to_dict()
        self.conn.execute(
            "INSERT INTO checks(domain, available, price, renewal_price, currency, premium, provider, expiration, registrar, status, error)"
            " VALUES(:domain, :available, :price, :renewal_price, :currency, :premium, :provider, :expiration, :registrar, :status, :error)",
            {**d, "available": None if d["available"] is None else int(d["available"]),
             "premium": None if d["premium"] is None else int(d["premium"])},
        )
        self.conn.commit()

    def history(self, domain: str, limit: int = 50) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM checks WHERE domain=? ORDER BY id DESC LIMIT ?", (domain, limit)
        ).fetchall()

    def last_check(self, domain: str) -> Optional[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM checks WHERE domain=? ORDER BY id DESC LIMIT 1", (domain,)
        ).fetchone()

    def price_stats(self, domain: str) -> dict[str, Any]:
        rows = self.conn.execute(
            "SELECT price FROM checks WHERE domain=? AND price IS NOT NULL ORDER BY id", (domain,)
        ).fetchall()
        prices = [r["price"] for r in rows]
        if not prices:
            return {}
        return {"lowest": min(prices), "highest": max(prices), "current": prices[-1],
                "average": sum(prices) / len(prices), "samples": len(prices)}

    def record_event(self, type: str, domain: str, message: str, data: Optional[dict] = None) -> None:
        self.conn.execute(
            "INSERT INTO events(type, domain, message, data) VALUES(?,?,?,?)",
            (type, domain, message, json.dumps(data or {})),
        )
        self.conn.commit()

    def recent_event(self, type: str, domain: str, since_seconds: float) -> Optional[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM events WHERE type=? AND domain=? AND timestamp >= datetime('now', ?) ORDER BY id DESC LIMIT 1",
            (type, domain, f"-{int(since_seconds)} seconds"),
        ).fetchone()

    def events(self, domain: Optional[str] = None, limit: int = 50) -> list[sqlite3.Row]:
        if domain:
            return self.conn.execute(
                "SELECT * FROM events WHERE domain=? ORDER BY id DESC LIMIT ?", (domain, limit)
            ).fetchall()
        return self.conn.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

    def record_dns(self, domain: str, record_type: str, value: str) -> None:
        self.conn.execute("INSERT INTO dns(domain, record_type, value) VALUES(?,?,?)",
                          (domain, record_type, value))
        self.conn.commit()
