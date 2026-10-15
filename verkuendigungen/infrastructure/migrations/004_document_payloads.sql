CREATE TABLE document_payloads (
    id INTEGER PRIMARY KEY,
    template_id INTEGER NOT NULL,
    template_docx BLOB NOT NULL,
    payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),
    revision INTEGER NOT NULL DEFAULT 1,
    generated_docx BLOB,
    generated_pdf BLOB,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
