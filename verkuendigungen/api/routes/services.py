import sqlite3
from datetime import date, timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, Query, HTTPException, Response
from pydantic import Field, model_validator
from ..dependencies import get_database
from ...schemas.documents import Model, Service
from ...services.dated_services import read_services, save_services

router = APIRouter(prefix='/services', tags=['Gottesdienste'])
Connection = Annotated[sqlite3.Connection, Depends(get_database)]
Parish = Annotated[str, Query(min_length=1, max_length=120)]

class ServicesInput(Model):
    services: list[Service] = Field(max_length=30)
    revision: int = Field(ge=0)

    @model_validator(mode='after')
    def unique_ids(self):
        ids=[]
        for service in self.services:
            ids += [service.id] + [s.id for s in [*service.intentions,*service.notices]]
        if len(ids) != len(set(ids)):
            raise ValueError('Die Eintraege benoetigen eindeutige IDs.')
        return self

@router.get('')
def services_range(parish: Parish, start: date, end: date, conn: Connection, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    if not parish.strip() or end < start or (end-start).days > 31:
        raise HTTPException(422, 'Bitte Pfarre und einen Zeitraum von maximal 32 Tagen angeben.')
    return {'items': [{'date': (start+timedelta(days=i)).isoformat(), **read_services(conn, parish.strip(), start+timedelta(days=i))} for i in range((end-start).days+1)]}

@router.get('/{day}')
def get_services(day: date, parish: Parish, conn: Connection, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    if not parish.strip():
        raise HTTPException(422, 'Eine Pfarre ist erforderlich.')
    return read_services(conn, parish.strip(), day)

@router.put('/{day}')
def put_services(day: date, parish: Parish, payload: ServicesInput, conn: Connection):
    if not parish.strip():
        raise HTTPException(422, 'Eine Pfarre ist erforderlich.')
    with conn:
        save_services(conn, parish.strip(), day, payload.services, payload.revision)
    return read_services(conn, parish.strip(), day)
