CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL,
    timestamp TEXT DEFAULT (datetime('now')),
    price REAL,
    renewal_price REAL,
    currency TEXT
);
CREATE INDEX IF NOT EXISTS idx_price_history_domain ON price_history(domain);
