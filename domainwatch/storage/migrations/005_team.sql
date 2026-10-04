CREATE TABLE IF NOT EXISTS api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    name TEXT,
    role TEXT DEFAULT 'viewer',   -- admin | operator | viewer | auditor
    team TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    revoked INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT (datetime('now')),
    actor TEXT,
    action TEXT,
    target TEXT,
    detail TEXT
);
