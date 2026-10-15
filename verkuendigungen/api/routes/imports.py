import json
import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends

from ..dependencies import get_database

router = APIRouter(prefix='/imports', tags=['Importstatus'])


@router.get('')
def list_imports(conn: Annotated[sqlite3.Connection, Depends(get_database)]):
    rows = [dict(row) for row in conn.execute('SELECT * FROM import_runs ORDER BY id DESC')]
    for row in rows:
        row['report'] = json.loads(row.pop('report_json'))
    return rows
