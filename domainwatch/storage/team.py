from __future__ import annotations

import secrets
import sqlite3
from typing import Optional

ROLES = ["admin", "operator", "viewer", "auditor"]
ROLE_RANK = {"admin": 4, "operator": 3, "viewer": 2, "auditor": 1}


def create_key(conn: sqlite3.Connection, name: str, role: str = "viewer", team: str = "default") -> str:
    if role not in ROLES:
        raise ValueError(f"role must be one of {ROLES}")
    key = "dwk_" + secrets.token_urlsafe(24)
    conn.execute("INSERT INTO api_keys(key, name, role, team) VALUES(?,?,?,?)", (key, name, role, team))
    conn.commit()
    return key


def validate_key(conn: sqlite3.Connection, key: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM api_keys WHERE key=? AND revoked=0", (key,)).fetchone()


def revoke_key(conn: sqlite3.Connection, key: str) -> None:
    conn.execute("UPDATE api_keys SET revoked=1 WHERE key=?", (key,))
    conn.commit()


def list_keys(conn: sqlite3.Connection):
    return conn.execute("SELECT name, role, team, created_at, revoked FROM api_keys").fetchall()


def audit(conn: sqlite3.Connection, actor: str, action: str, target: str = "", detail: str = "") -> None:
    conn.execute("INSERT INTO audit_logs(actor, action, target, detail) VALUES(?,?,?,?)",
                 (actor, action, target, detail))
    conn.commit()


def audit_log(conn: sqlite3.Connection, limit: int = 50):
    return conn.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
