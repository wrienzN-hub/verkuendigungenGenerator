import json
import sqlite3
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile

from ...services.directorium import ImportConflict, import_pdf

from ..dependencies import get_database

router = APIRouter(prefix='/imports', tags=['Directorium'])
Connection = Annotated[sqlite3.Connection, Depends(get_database)]
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


@router.get('')
def list_imports(conn: Connection):
    rows = [dict(row) for row in conn.execute(
        'SELECT id,source_file,source_sha256,liturgical_year,diocese,parser_version,imported_at,report_json,source_pdf IS NOT NULL AS has_source FROM import_runs ORDER BY id DESC'
    )]
    for row in rows:
        row['has_source'] = bool(row['has_source'])
        row['report'] = json.loads(row.pop('report_json'))
    return rows


@router.post('/directorium', status_code=201)
def upload_directorium(conn: Connection, response: Response, file: UploadFile = File(...)):
    try:
        if not file.filename or not file.filename.lower().endswith('.pdf'):
            raise HTTPException(415, 'Bitte ein Directorium als PDF-Datei hochladen.')
        data = file.file.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, 'Die PDF-Datei darf höchstens 25 MB groß sein.')
        result = import_pdf(conn, pdf_bytes=data, filename=file.filename)
        if result['already_imported']:
            response.status_code = 200
        return result
    except ImportConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, 'Dieses Kirchenjahr wurde inzwischen bereits importiert. Bitte die Liste neu laden.') from exc
    finally:
        file.file.close()


@router.get('/{import_id}/source')
def download_source(import_id: int, conn: Connection):
    row = conn.execute('SELECT source_file,source_pdf FROM import_runs WHERE id=?', (import_id,)).fetchone()
    if row is None or row['source_pdf'] is None:
        raise HTTPException(404, 'Die Originaldatei ist nicht verfügbar.')
    return Response(row['source_pdf'], media_type='application/pdf', headers={
        'Content-Disposition': "inline; filename*=UTF-8''" + quote(row['source_file'], safe=''),
    })
