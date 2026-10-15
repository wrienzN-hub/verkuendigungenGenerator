import json
import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ..dependencies import get_database
from ...schemas.documents import ParishDefaults

router = APIRouter(prefix='/settings', tags=['Pfarrvorgaben'])
Connection = Annotated[sqlite3.Connection, Depends(get_database)]
ParishName = Annotated[str, Query(min_length=1, max_length=120, pattern=r'.*\S.*')]


@router.get('')
def read_settings(conn: Connection, parish: ParishName):
    row = conn.execute('SELECT settings_json FROM parish_defaults WHERE parish_name=?', (parish.strip(),)).fetchone()
    return json.loads(row[0]) if row else ParishDefaults().model_dump(mode='json', by_alias=True)


@router.put('')
def save_settings(conn: Connection, parish: ParishName, payload: ParishDefaults):
    with conn:
        conn.execute("INSERT INTO parish_defaults(parish_name,settings_json) VALUES(?,?) ON CONFLICT(parish_name) DO UPDATE SET settings_json=excluded.settings_json,updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now')", (parish.strip(), payload.model_dump_json(by_alias=True)))
    return payload.model_dump(mode='json', by_alias=True)
