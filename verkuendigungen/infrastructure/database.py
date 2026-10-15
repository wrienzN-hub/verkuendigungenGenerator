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
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        yield conn
    finally:
        conn.close()


def migrate(conn):
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version > 1:
        raise ValueError("Die Datenbank ist neuer als diese Anwendung.")
    if version == 0:
        sql = (Path(__file__).parent / "migrations/001_initial.sql").read_text(encoding="utf-8")
        try:
            conn.executescript("BEGIN IMMEDIATE;\n" + sql + "\nPRAGMA user_version = 1;\nCOMMIT;")
        except Exception:
            conn.rollback()
            raise
