import hashlib
import sqlite3
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from ..dependencies import get_database
from ...schemas.documents import DocumentPayload, PrepareDocument, SaveDocument
from ...services.dated_services import sync_document_services
from ...services.documents import generation_weeks, options, prepare, read_document, template_source, validate_selection
from ...services.document_rendering import ConversionError, additional_lines, bilingual, converter_available, convert_pdf, render_docx

router = APIRouter(prefix='/documents', tags=['Verkündigungen'])
Connection = Annotated[sqlite3.Connection, Depends(get_database)]


@router.get('/options')
def document_options(conn: Connection):
    return {**options(conn), 'preview_available': converter_available()}


@router.get('/weeks')
def weeks(conn: Connection, year: Annotated[str, Query(pattern=r'^20\d{2}/\d{2}$')]):
    return generation_weeks(conn, year)


@router.post('/prepare')
def prepare_document(payload: PrepareDocument, conn: Connection):
    try:
        return prepare(conn, payload.template_id, payload.year, payload.week_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get('')
def list_documents(conn: Connection, limit: Annotated[int, Query(ge=1, le=100)] = 20, offset: Annotated[int, Query(ge=0)] = 0):
    rows = conn.execute("SELECT id,revision,created_at,updated_at,generated_docx IS NOT NULL AS has_docx, json_extract(payload_json,'$.parish.name.de') AS parish_name, json_extract(payload_json,'$.period.start') AS start, json_extract(payload_json,'$.period.end') AS end FROM document_payloads ORDER BY updated_at DESC,id DESC LIMIT ? OFFSET ?", (limit, offset))
    return {'items': [{**dict(row), 'has_docx': bool(row['has_docx'])} for row in rows], 'total': conn.execute('SELECT count(*) FROM document_payloads').fetchone()[0]}


@router.post('', status_code=201)
def create_document(body: SaveDocument, conn: Connection):
    payload = body.payload
    try:
        validate_selection(conn, payload)
        template = template_source(conn, payload.template_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if payload.template_version != hashlib.sha256(template['docx']).hexdigest():
        raise HTTPException(409, 'Die Vorlage wurde geändert. Bitte einen neuen Entwurf laden.')
    with conn:
        sync_document_services(conn, payload)
        cursor = conn.execute('INSERT INTO document_payloads(template_id,template_docx,payload_json) VALUES(?,?,?)', (payload.template_id, template['docx'], payload.model_dump_json(by_alias=True)))
    return read_document(conn, cursor.lastrowid)


@router.get('/{document_id}')
def get_document(document_id: int, conn: Connection):
    try:
        return read_document(conn, document_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.put('/{document_id}')
def update_document(document_id: int, body: SaveDocument, conn: Connection):
    current = get_document(document_id, conn)
    if body.revision != current['revision']:
        raise HTTPException(409, 'Der Entwurf wurde inzwischen geändert. Bitte erneut öffnen.')
    before = current['payload']
    for key in ['template_id', 'template_version', 'selection', 'period']:
        if body.payload.model_dump(mode='json')[key] != before[key]:
            raise HTTPException(422, 'Für eine andere Vorlage oder Woche bitte einen neuen Entwurf laden.')
    with conn:
        sync_document_services(conn, body.payload, before)
        cursor = conn.execute("UPDATE document_payloads SET payload_json=?, revision=revision+1, generated_pdf=NULL, generated_docx=NULL, updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id=? AND revision=?", (body.payload.model_dump_json(by_alias=True), document_id, body.revision))
        if cursor.rowcount != 1:
            raise HTTPException(409, 'Der Entwurf wurde inzwischen geändert. Bitte erneut öffnen.')
    return read_document(conn, document_id)


def generate(document_id, conn, revision, preview=False):
    current = get_document(document_id, conn)
    if current['revision'] != revision:
        raise HTTPException(409, 'Der Entwurf wurde inzwischen geändert. Bitte erneut öffnen.')
    payload = DocumentPayload.model_validate(current['payload'])
    visible = any(day.enabled for day in payload.days)
    if not visible and not additional_lines(payload):
        raise HTTPException(422, 'Bitte mindestens einen sichtbaren Gottesdienst, Gedenktag, Hinweis oder Termin ergänzen.')
    template = conn.execute('SELECT template_docx FROM document_payloads WHERE id=?', (document_id,)).fetchone()[0]
    try:
        docx = render_docx(template, payload)
        pdf = convert_pdf(docx) if preview else None
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except ConversionError as exc:
        raise HTTPException(503, str(exc)) from exc
    with conn:
        cursor = conn.execute('UPDATE document_payloads SET generated_docx=?,generated_pdf=coalesce(?,generated_pdf) WHERE id=? AND revision=?', (docx, pdf, document_id, revision))
        if cursor.rowcount != 1:
            raise HTTPException(409, 'Während der Dokumenterstellung wurde der Entwurf geändert. Bitte erneut erstellen.')
    return {'id': document_id, 'revision': revision, 'docx_url': f'/api/v1/documents/{document_id}/docx', 'preview_url': f'/api/v1/documents/{document_id}/preview?revision={revision}' if preview else None}


@router.post('/{document_id}/generate')
def generate_document(document_id: int, conn: Connection, revision: Annotated[int, Query(ge=1)]):
    return generate(document_id, conn, revision)


@router.post('/{document_id}/preview')
def generate_preview(document_id: int, conn: Connection, revision: Annotated[int, Query(ge=1)]):
    return generate(document_id, conn, revision, preview=True)


@router.get('/{document_id}/preview')
def document_preview(document_id: int, conn: Connection, revision: Annotated[int, Query(ge=1)]):
    current = get_document(document_id, conn)
    if current['revision'] != revision:
        raise HTTPException(409, 'Die Vorschau ist veraltet. Bitte erneut laden.')
    row = conn.execute('SELECT generated_pdf FROM document_payloads WHERE id=?', (document_id,)).fetchone()
    if row[0] is None:
        raise HTTPException(404, 'Für diesen Stand wurde noch keine Dokumentvorschau erstellt.')
    return Response(row[0], media_type='application/pdf', headers={'Content-Disposition': 'inline', 'Cache-Control': 'no-store'})


@router.get('/{document_id}/docx')
def download_word(document_id: int, conn: Connection):
    current = get_document(document_id, conn)
    row = conn.execute('SELECT generated_docx FROM document_payloads WHERE id=?', (document_id,)).fetchone()
    if row[0] is None:
        raise HTTPException(404, 'Für diesen Stand wurde noch kein Word-Dokument erstellt.')
    filename = 'Verkuendigung_' + current['payload']['period']['start'] + '.docx'
    return Response(row[0], media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document', headers={'Content-Disposition': "attachment; filename*=UTF-8''" + quote(filename, safe=''), 'Cache-Control': 'no-store'})


@router.delete('/{document_id}')
def delete_document(document_id: int, conn: Connection, revision: Annotated[int, Query(ge=1)]):
    current = get_document(document_id, conn)
    if current['revision'] != revision:
        raise HTTPException(409, 'Die Verkündigung wurde inzwischen geändert. Bitte die Liste neu laden.')
    with conn:
        cursor = conn.execute('DELETE FROM document_payloads WHERE id=? AND revision=?', (document_id, revision))
        if cursor.rowcount != 1:
            raise HTTPException(409, 'Die Verkündigung wurde inzwischen geändert. Bitte die Liste neu laden.')
    return {'deleted': True, 'id': document_id}
