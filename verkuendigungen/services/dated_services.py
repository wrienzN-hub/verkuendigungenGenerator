import json
from fastapi import HTTPException
from ..schemas.documents import Service


def read_services(conn, parish, day):
    row = conn.execute('SELECT services_json,revision FROM dated_services WHERE parish_name=? AND service_date=?', (parish, str(day))).fetchone()
    if row:
        services = [Service.model_validate(s) for s in json.loads(row[0])]
        for service in services:
            service.title.de = service.title.sl = ''
            service.title.de_marks = service.title.sl_marks = []
        return {'services': [s.model_dump(mode='json') for s in services], 'revision': row[1]}
    return {'services': [], 'revision': 0}


def save_services(conn, parish, day, services, revision):
    current = read_services(conn, parish, day)
    values = [s.model_dump(mode='json') for s in services]
    if values == current['services'] and current['revision']:
        return current['revision']
    if revision != current['revision']:
        raise HTTPException(409, 'Die Gottesdienste fuer ' + str(day) + ' wurden inzwischen geaendert. Bitte die Woche neu laden.')
    new_revision = revision + 1
    cursor = conn.execute('INSERT INTO dated_services(parish_name,service_date,services_json,revision) VALUES(?,?,?,?) ON CONFLICT(parish_name,service_date) DO UPDATE SET services_json=excluded.services_json,revision=excluded.revision WHERE dated_services.revision=?', (parish, str(day), json.dumps(values,ensure_ascii=False), new_revision, revision))
    if cursor.rowcount != 1:
        raise HTTPException(409, 'Die Gottesdienste wurden inzwischen geaendert. Bitte erneut laden.')
    return new_revision


def sync_document_services(conn, payload, before=None):
    previous = {d['date']: d for d in before['days']} if before else {}
    for day in payload.days:
        old = previous.get(day.date.isoformat())
        if old and [Service.model_validate(s).model_dump(mode='json') for s in old['services']] == [s.model_dump(mode='json') for s in day.services]:
            continue
        day.services_revision = save_services(conn, payload.parish.id, day.date, day.services, day.services_revision)
