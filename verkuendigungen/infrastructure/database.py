"""SQLite-Verbindung und versionierte, transaktionale Migrationen."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from ..core.config import DEFAULT_DATABASE


@contextmanager
def database(path=DEFAULT_DATABASE):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # FastAPI darf eine Anfrage zwischen Worker-Threads fortsetzen.
    # Jede Anfrage erhält ihre eigene Verbindung, keine globale Verbindung.
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.create_function('casefold', 1, lambda value: (value or '').casefold(), deterministic=True)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        yield conn
    finally:
        conn.close()


def migrate(conn):
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version > 8:
        raise ValueError("Die Datenbank ist neuer als diese Anwendung.")
    for migration in sorted((Path(__file__).parent / 'migrations').glob('*.sql')):
        target = int(migration.name.split('_')[0])
        if target <= version:
            continue
        sql = migration.read_text(encoding='utf-8')
        try:
            conn.executescript("BEGIN IMMEDIATE;\n" + sql + f"\nPRAGMA user_version = {target};\nCOMMIT;")
        except Exception:
            conn.rollback()
            raise
        version = target
