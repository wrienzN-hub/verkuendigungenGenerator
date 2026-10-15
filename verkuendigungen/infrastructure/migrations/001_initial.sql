CREATE TABLE import_runs (
    id INTEGER PRIMARY KEY,
    source_file TEXT NOT NULL,
    source_sha256 TEXT NOT NULL UNIQUE,
    liturgical_year TEXT NOT NULL,
    diocese TEXT NOT NULL DEFAULT 'gurk',
    parser_version TEXT NOT NULL,
    imported_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    status TEXT NOT NULL CHECK(status IN ('imported_needs_review','reviewed')),
    report_json TEXT NOT NULL CHECK(json_valid(report_json))
);

CREATE TABLE source_pages (
    import_run_id INTEGER NOT NULL REFERENCES import_runs(id),
    pdf_page INTEGER NOT NULL CHECK(pdf_page > 0),
    printed_page TEXT,
    raw_text TEXT NOT NULL,
    PRIMARY KEY (import_run_id, pdf_page)
);

CREATE TABLE calendar_days (
    id INTEGER PRIMARY KEY,
    import_run_id INTEGER NOT NULL REFERENCES import_runs(id),
    liturgical_year TEXT NOT NULL,
    calendar_date TEXT NOT NULL CHECK(date(calendar_date) IS NOT NULL AND calendar_date = date(calendar_date)),
    weekday TEXT NOT NULL CHECK(weekday IN ('Mo','Di','Mi','Do','Fr','Sa','So')),
    UNIQUE(import_run_id, calendar_date)
);

CREATE TABLE source_day_blocks (
    id INTEGER PRIMARY KEY,
    calendar_day_id INTEGER NOT NULL REFERENCES calendar_days(id),
    variant INTEGER NOT NULL,
    header_text TEXT NOT NULL,
    header_notes TEXT NOT NULL,
    source_page_start INTEGER NOT NULL,
    source_page_end INTEGER NOT NULL,
    raw_text TEXT NOT NULL,
    UNIQUE(calendar_day_id, variant)
);

-- Ein Datensatz pro liturgischer Feier; gemeinsam gefeierte Heilige bleiben
-- wie im Directorium zusammen. Auch Sonntage und Herrenfeste sind Feiern.
CREATE TABLE saints (
    id INTEGER PRIMARY KEY,
    calendar_day_id INTEGER NOT NULL REFERENCES calendar_days(id),
    source_block_id INTEGER NOT NULL REFERENCES source_day_blocks(id),
    source_key TEXT NOT NULL UNIQUE,
    liturgical_year TEXT NOT NULL,
    celebration_date TEXT NOT NULL CHECK(date(celebration_date) IS NOT NULL AND celebration_date = date(celebration_date)),
    name TEXT NOT NULL CHECK(length(trim(name)) > 0),
    name_sl TEXT,
    kind TEXT NOT NULL CHECK(kind IN ('saint','marian','sunday','feast','commemoration')),
    rank_code TEXT CHECK(rank_code IN ('H','F','G','g','sunday','privileged_weekday','triduum','octave','commemoration')),
    calendar_scope TEXT NOT NULL,
    applicability_note TEXT,
    observance_status TEXT NOT NULL CHECK(observance_status IN ('observed','optional','commemoration_only','suppressed','conditional')),
    disabled INTEGER NOT NULL DEFAULT 0 CHECK(disabled IN (0,1)),
    source_page INTEGER NOT NULL,
    source_reference TEXT NOT NULL,
    source_text TEXT NOT NULL,
    review_status TEXT NOT NULL DEFAULT 'needs_review' CHECK(review_status IN ('needs_review','reviewed')),
    review_notes TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE(source_block_id, name)
);

CREATE INDEX saints_date_idx ON saints(liturgical_year, celebration_date);
CREATE INDEX saints_status_idx ON saints(disabled, observance_status);

CREATE VIEW available_celebrations AS
SELECT * FROM saints
WHERE disabled = 0
  AND observance_status IN ('observed','optional','commemoration_only');

-- Bedingte lokale Feiern müssen bewusst ausgewählt werden. Die Rangcodes
-- sind keine vollständige numerische Vorrangtabelle des Kirchenjahres.
