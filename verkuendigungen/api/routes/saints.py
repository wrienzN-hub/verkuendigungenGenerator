import sqlite3
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from ...repositories.saints import get_saint, list_celebrations, count_celebrations, update_saint as save_saint
from ...schemas.saints import Saint, SaintUpdate, SaintPage, Rank, Observance
from ..dependencies import get_database
from ...services.liturgical_weeks import list_weeks

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


@router.get('/page', response_model=SaintPage)
def paged_saints(conn: Connection,
    start: date = date(1,1,1), end: date = date(9999,12,31),
    year: str | None = None, search: Annotated[str | None,Query(max_length=200)] = None,
    disabled: bool | None = None, month: Annotated[int | None,Query(ge=1,le=12)] = None,
    rank: Rank | None = None, observance_status: Observance | None = None,
    liturgical_week: Annotated[str | None,Query(max_length=80)] = None,
    limit: Annotated[int,Query(ge=1,le=1000)] = 25, offset: Annotated[int,Query(ge=0)] = 0):
    if start>end:
        raise HTTPException(422,'Das Ende liegt vor dem Beginn.')
    if liturgical_week:
        if not year:
            raise HTTPException(422,'Für eine liturgische Woche ist ein Kirchenjahr erforderlich.')
        selected = next((w for w in list_weeks(conn,year) if w['id']==liturgical_week),None)
        if selected is None:
            raise HTTPException(422,'Diese liturgische Woche ist im gewählten Directorium nicht vorhanden.')
        start=max(start,date.fromisoformat(selected['start']))
        end=min(end,date.fromisoformat(selected['end']))
        if start>end:
            return dict(items=[],total=0,limit=limit,offset=offset)
    filters=dict(available_only=False,year=year,search=search,disabled=disabled,month=month,rank=rank,observance_status=observance_status)
    return dict(items=list_celebrations(conn,start.isoformat(),end.isoformat(),limit=limit,offset=offset,**filters),
        total=count_celebrations(conn,start.isoformat(),end.isoformat(),**filters),limit=limit,offset=offset)


@router.get('/weeks')
def week_options(conn: Connection, year: Annotated[str,Query(max_length=20)]):
    return list_weeks(conn,year)


@router.get('/filters')
def filter_options(conn: Connection):
    return {
        'years':[r[0] for r in conn.execute('SELECT DISTINCT liturgical_year FROM saints ORDER BY liturgical_year DESC')],
        'total':conn.execute('SELECT count(*) FROM saints').fetchone()[0],
        'active':conn.execute('SELECT count(*) FROM saints WHERE disabled=0').fetchone()[0],
    }


@router.get('/{saint_id}', response_model=Saint)
def read_saint(saint_id: int, conn: Connection):
    row = get_saint(conn, saint_id)
    if row is None:
        raise HTTPException(404, 'Eintrag nicht gefunden.')
    return row


@router.patch('/{saint_id}', response_model=Saint)
def update_saint(saint_id: int, payload: SaintUpdate, conn: Connection):
    try:
        save_saint(conn, saint_id, payload.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409,'Eine Feier mit diesem Namen existiert bereits im selben Quellenabschnitt.') from exc
    return get_saint(conn, saint_id)
