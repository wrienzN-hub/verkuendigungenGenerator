import json
import sqlite3

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from ..dependencies import get_database
from ...schemas.events import EventInput, EventUpdate

router = APIRouter(prefix='/events', tags=['Termine'])
Connection = Annotated[sqlite3.Connection, Depends(get_database)]


def event(row):
    result = dict(row)
    result = {key: result[key] for key in ['id', 'name', 'revision', 'created_at', 'updated_at', 'text_json', 'parishes_json', 'weeks_json']}
    for key in ['text', 'parishes', 'weeks']:
        result[key] = json.loads(result.pop(key + '_json'))
    return result


def read(conn, id_):
    row = conn.execute('SELECT * FROM events WHERE id=?', (id_,)).fetchone()
    if row is None:
        raise HTTPException(404, 'Termin nicht gefunden.')
    return event(row)


@router.get('')
def list_events(conn: Connection, parish: Annotated[str | None, Query(max_length=120)] = None, search: Annotated[str | None, Query(max_length=200)] = None, year: str | None = None, week_id: str | None = None, limit: Annotated[int, Query(ge=1, le=100)] = 20, offset: Annotated[int, Query(ge=0)] = 0):
    clauses, params = [], []
    if parish:
        clauses.append('EXISTS (SELECT 1 FROM json_each(parishes_json) WHERE value=? COLLATE NOCASE)'); params.append(parish)
    if search:
        clauses.append('(instr(casefold(name),casefold(?))>0 OR instr(casefold(text_json),casefold(?))>0)'); params.extend([search, search])
    if year and week_id:
        clauses.append("EXISTS (SELECT 1 FROM json_each(weeks_json) WHERE json_extract(value,'$.year')=? AND json_extract(value,'$.week_id')=?)")
        params.extend([year, week_id])
    where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
    total = conn.execute('SELECT count(*) FROM events' + where, params).fetchone()[0]
    rows = conn.execute('SELECT * FROM events' + where + ' ORDER BY name COLLATE NOCASE,id LIMIT ? OFFSET ?', [*params, limit, offset])
    return {'items': [event(row) for row in rows], 'total': total}


def values(conn, payload):
    from ...services.documents import generation_weeks
    for week in payload.weeks:
        if not any(w['id'] == week.week_id for w in generation_weeks(conn, week.year)):
            raise HTTPException(422, 'Die liturgische Woche ist nicht vorhanden.')
    return (payload.name, json.dumps(payload.parishes), json.dumps([w.model_dump() for w in payload.weeks]), payload.text.model_dump_json())



@router.post('', status_code=201)
def create_event(conn: Connection, payload: EventInput):
    with conn:
        cursor = conn.execute("INSERT INTO events(name,parishes_json,weeks_json,text_json,parish_name,title_json) VALUES(?,?,?,?,'','{}')", values(conn, payload))
    return read(conn, cursor.lastrowid)


@router.get('/{id_}')
def get_event(id_: int, conn: Connection):
    return read(conn, id_)


@router.put('/{id_}')
def update_event(id_: int, conn: Connection, payload: EventUpdate):
    read(conn, id_)
    with conn:
        cursor = conn.execute("UPDATE events SET name=?,parishes_json=?,weeks_json=?,text_json=?,revision=revision+1,updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id=? AND revision=?", (*values(conn, payload), id_, payload.revision))
        if cursor.rowcount != 1:
            raise HTTPException(409, 'Der Termin wurde inzwischen geändert. Bitte erneut öffnen.')
    return read(conn, id_)


@router.delete('/{id_}')
def delete_event(id_: int, conn: Connection, revision: Annotated[int, Query(ge=1)]):
    read(conn, id_)
    with conn:
        cursor = conn.execute('DELETE FROM events WHERE id=? AND revision=?', (id_, revision))
        if cursor.rowcount != 1:
            raise HTTPException(409, 'Der Termin wurde inzwischen geändert. Bitte die Liste neu laden.')
    return {'deleted': True}
