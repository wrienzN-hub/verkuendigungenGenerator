import hashlib
import sqlite3
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile

from ..dependencies import get_database
from ...services.templates import validate_docx

router = APIRouter(prefix='/templates', tags=['Word-Vorlagen'])
Connection = Annotated[sqlite3.Connection, Depends(get_database)]
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
METADATA = 'id, parish_name, name, source_filename, file_size, created_at'
DOCX_TYPE = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'


@router.get('')
def list_templates(conn: Connection):
    return [dict(row) for row in conn.execute(f'SELECT {METADATA} FROM document_templates ORDER BY casefold(parish_name), casefold(name)')]


@router.post('', status_code=201)
def upload_template(conn: Connection, file: UploadFile = File(...), parish_name: str = Form(...), name: str = Form(...)):
    try:
        parish_name, name = parish_name.strip(), name.strip()
        if not parish_name or not name or len(parish_name) > 120 or len(name) > 120:
            raise HTTPException(422, 'Pfarre und Vorlagenname müssen zwischen 1 und 120 Zeichen enthalten.')
        filename = (file.filename or '').replace('\\', '/').rsplit('/', 1)[-1]
        if not filename.lower().endswith('.docx'):
            raise HTTPException(415, 'Bitte eine Word-Datei im DOCX-Format auswählen.')
        data = file.file.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, 'Die Word-Datei darf höchstens 25 MB groß sein.')
        try:
            validate_docx(data)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        try:
            with conn:
                cursor = conn.execute('INSERT INTO document_templates(parish_name,name,source_filename,file_size,source_sha256,docx) VALUES(?,?,?,?,?,?)', (parish_name, name, filename, len(data), hashlib.sha256(data).hexdigest(), data))
        except sqlite3.IntegrityError as exc:
            raise HTTPException(409, 'Für diese Pfarre gibt es bereits eine Vorlage mit diesem Namen. Bitte einen anderen Namen verwenden.') from exc
        return dict(conn.execute(f'SELECT {METADATA} FROM document_templates WHERE id=?', (cursor.lastrowid,)).fetchone())
    finally:
        file.file.close()


@router.get('/{template_id}/source')
def download_template(template_id: int, conn: Connection):
    row = conn.execute('SELECT source_filename,docx FROM document_templates WHERE id=?', (template_id,)).fetchone()
    if row is None:
        raise HTTPException(404, 'Vorlage nicht gefunden.')
    return Response(row['docx'], media_type=DOCX_TYPE, headers={'Content-Disposition': "attachment; filename*=UTF-8''" + quote(row['source_filename'], safe='')})
