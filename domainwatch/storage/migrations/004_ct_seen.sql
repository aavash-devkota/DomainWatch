CREATE TABLE IF NOT EXISTS ct_seen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL,
    seen_at TEXT DEFAULT (datetime('now')),
    issuer_name TEXT,
    name_value TEXT,
    not_before TEXT,
    cert_id TEXT,
    UNIQUE(domain, cert_id)
);
