from __future__ import annotations

import sqlite3
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def current_version(conn: sqlite3.Connection) -> int:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT DEFAULT (datetime('now')))"
    )
    row = conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations").fetchone()
    return int(row[0])


def migrate(conn: sqlite3.Connection) -> list[int]:
    applied = []
    v = current_version(conn)
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        num = int(path.name.split("_")[0])
        if num > v:
            conn.executescript(path.read_text())
            conn.execute("INSERT INTO schema_migrations(version) VALUES(?)", (num,))
            applied.append(num)
    conn.commit()
    return applied


def status(conn: sqlite3.Connection) -> dict:
    v = current_version(conn)
    files = sorted(p.name for p in MIGRATIONS_DIR.glob("*.sql"))
    return {"current_version": v, "available_migrations": files}
