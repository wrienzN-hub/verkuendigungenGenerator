CREATE TABLE parish_defaults (
    parish_name TEXT PRIMARY KEY COLLATE NOCASE,
    settings_json TEXT NOT NULL CHECK(json_valid(settings_json)),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
