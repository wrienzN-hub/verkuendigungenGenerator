CREATE TABLE document_templates (
    id INTEGER PRIMARY KEY,
    parish_name TEXT NOT NULL,
    name TEXT NOT NULL,
    source_filename TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    source_sha256 TEXT NOT NULL,
    docx BLOB NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE UNIQUE INDEX document_template_names ON document_templates(parish_name COLLATE NOCASE, name COLLATE NOCASE);
