CREATE TABLE IF NOT EXISTS dns_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL,
    timestamp TEXT DEFAULT (datetime('now')),
    record_type TEXT,
    value TEXT,
    hash TEXT
);
CREATE INDEX IF NOT EXISTS idx_dns_history_domain ON dns_history(domain);
