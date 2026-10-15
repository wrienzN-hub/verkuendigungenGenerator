CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parish_name TEXT NOT NULL,
    event_date TEXT,
    title_json TEXT NOT NULL CHECK(json_valid(title_json)),
    text_json TEXT NOT NULL CHECK(json_valid(text_json)),
    event_time TEXT,
    location TEXT NOT NULL DEFAULT '',
    revision INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE INDEX events_parish_date ON events(parish_name COLLATE NOCASE,event_date);
