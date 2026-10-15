import sqlite3
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from ...repositories.saints import get_saint, list_celebrations, set_disabled
from ...schemas.saints import Saint, SaintUpdate
from ..dependencies import get_database

router = APIRouter(prefix='/saints', tags=['Heilige und Feiern'])
Connection = Annotated[sqlite3.Connection, Depends(get_database)]


@router.get('', response_model=list[Saint])
def list_saints(
    conn: Connection,
    start: date = date(1, 1, 1),
    end: date = date(9999, 12, 31),
    year: str | None = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    disabled: bool | None = None,
    available_only: bool = False,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    if start > end:
        raise HTTPException(422, 'Das Ende liegt vor dem Beginn.')
    return list_celebrations(conn, start.isoformat(), end.isoformat(),
                             year=year, search=search, disabled=disabled,
                             available_only=available_only, limit=limit, offset=offset)


@router.get('/{saint_id}', response_model=Saint)
def read_saint(saint_id: int, conn: Connection):
    row = get_saint(conn, saint_id)
    if row is None:
        raise HTTPException(404, 'Eintrag nicht gefunden.')
    return row


@router.patch('/{saint_id}', response_model=Saint)
def update_saint(saint_id: int, payload: SaintUpdate, conn: Connection):
    try:
        set_disabled(conn, saint_id, payload.disabled)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return get_saint(conn, saint_id)
