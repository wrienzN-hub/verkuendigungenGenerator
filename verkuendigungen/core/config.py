"""Lokale Standardpfade; Datenbankpfad per Umgebung überschreibbar."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def database_path():
    return Path(os.environ.get('VERKUENDIGUNGEN_DB', ROOT / 'data/verkuendigungen.sqlite3')).resolve()


DEFAULT_DATABASE = database_path()
