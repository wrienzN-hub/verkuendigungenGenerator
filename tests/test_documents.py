from copy import deepcopy
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from fastapi.testclient import TestClient
from lxml import etree as ET

from verkuendigungen.api.app import create_app
from verkuendigungen.infrastructure.database import database
from verkuendigungen.services.directorium import import_pdf
from verkuendigungen.services.document_rendering import ConversionError, render_docx
from verkuendigungen.schemas.documents import DocumentPayload


class DocumentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.temp.name) / 'base.sqlite3'
        with TestClient(create_app(cls.base)):
            with database(cls.base) as conn:
                import_pdf(conn)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / 'documents.sqlite3'
        self.path.write_bytes(self.base.read_bytes())
        self.client = TestClient(create_app(self.path))
        self.client.__enter__()
        result = self.client.post('/api/v1/documents/prepare', json={'template_id': 0, 'year': '2026/27', 'week_id': 'advent:2026-11-29'})
        self.assertEqual(result.status_code, 200, result.text)
        self.payload = result.json()['payload']

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.folder.cleanup()

    def save(self, payload=None):
        response = self.client.post('/api/v1/documents', json={'payload': payload or self.payload})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_prepare_real_advent_boundary_and_active_source_entries(self):
        self.assertEqual(self.payload['period'], {'start': '2026-11-29', 'end': '2026-12-06'})
        self.assertEqual(len(self.payload['days']), 8)
        self.assertEqual(self.payload['days'][0]['date'], '2026-11-29')
        self.assertEqual(self.payload['days'][-1]['date'], '2026-12-06')
        self.assertEqual(self.payload['days'][0]['services'], [])
        self.assertTrue(self.payload['days'][0]['celebrations'])
        with database(self.path) as conn:
            ids = [c['source_celebration_id'] for d in self.payload['days'] for c in d['celebrations']]
            self.assertTrue(all(conn.execute('SELECT disabled=0 AND observance_status NOT IN (\'suppressed\',\'conditional\') FROM saints WHERE id=?', (id_,)).fetchone()[0] for id_ in ids))
            for day in self.payload['days']:
                for celebration in day['celebrations']:
                    status = conn.execute('SELECT observance_status FROM saints WHERE id=?', (celebration['source_celebration_id'],)).fetchone()[0]
                    self.assertEqual(celebration['enabled'], status == 'observed')
        weeks = self.client.get('/api/v1/documents/weeks?year=2026%2F27').json()
        self.assertEqual(weeks[0]['start'], '2026-11-29')
        self.assertEqual(self.client.post('/api/v1/documents/prepare', json={'template_id': 0, 'year': '2026/27', 'week_id': 'invalid'}).status_code, 422)

    def test_save_reopen_snapshot_revision_and_pdf_invalidation(self):
        saved = self.save()
        id_ = saved['id']
        self.assertEqual(self.client.get(f'/api/v1/documents/{id_}').json()['payload'], self.payload)
        with patch('verkuendigungen.api.routes.documents.convert_pdf', return_value=b'%PDF-test'):
            self.assertEqual(self.client.post(f'/api/v1/documents/{id_}/generate?revision=1').status_code, 200)
        self.assertEqual(self.client.get(f'/api/v1/documents/{id_}/pdf').content, b'%PDF-test')
        payload = deepcopy(self.payload)
        payload['days'][0]['celebrations'][0]['title']['de'] = 'Manuell geändert'
        updated = self.client.put(f'/api/v1/documents/{id_}', json={'payload': payload, 'revision': 1})
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()['revision'], 2)
        self.assertFalse(updated.json()['has_pdf'])
        self.assertEqual(self.client.get(f'/api/v1/documents/{id_}/pdf').status_code, 404)
        self.assertEqual(self.client.put(f'/api/v1/documents/{id_}', json={'payload': payload, 'revision': 1}).status_code, 409)
        self.assertEqual(self.client.post(f'/api/v1/documents/{id_}/generate?revision=1').status_code, 409)
        with patch('verkuendigungen.api.routes.documents.convert_pdf', side_effect=ConversionError('Konvertierung fehlt')):
            self.assertEqual(self.client.post(f'/api/v1/documents/{id_}/generate?revision=2').status_code, 503)
        self.assertEqual(self.client.get(f'/api/v1/documents/{id_}').json()['payload'], payload)
        self.assertEqual(self.client.get('/api/v1/documents').json()['total'], 1)

    def test_validation_dates_ids_booleans_times_selection_and_empty_document(self):
        for modify in [lambda p: p['days'].pop(), lambda p: p['days'][1].update(date=p['days'][0]['date']), lambda p: p['days'][1].update(id=p['days'][0]['id']), lambda p: p['days'][0].update(enabled='yes'), lambda p: p['selection'].update(week=9)]:
            payload = deepcopy(self.payload)
            modify(payload)
            self.assertEqual(self.client.post('/api/v1/documents', json={'payload': payload}).status_code, 422)
        payload = deepcopy(self.payload)
        payload['days'][0]['services'] = [{'id': 'service', 'enabled': True, 'time': '25:00'}]
        self.assertEqual(self.client.post('/api/v1/documents', json={'payload': payload}).status_code, 422)
        for day in payload['days']:
            day['enabled'] = False
        payload['days'][0]['services'] = []
        saved = self.save(payload)
        self.assertEqual(self.client.post(f"/api/v1/documents/{saved['id']}/generate?revision=1").status_code, 422)

    def test_uploaded_template_is_snapshotted_and_parish_selected(self):
        source = Path('resources/vorlage.docx').read_bytes()
        response = self.client.post('/api/v1/templates', data={'parish_name': 'Edling', 'name': 'Standard'}, files={'file': ('edling.docx', source)})
        template_id = response.json()['id']
        payload = self.client.post('/api/v1/documents/prepare', json={'template_id': template_id, 'year': '2026/27', 'week_id': 'advent:2026-11-29'}).json()['payload']
        self.assertEqual(payload['parish']['name']['de'], 'Edling')
        saved = self.save(payload)
        with database(self.path) as conn:
            self.assertEqual(conn.execute('SELECT template_docx FROM document_payloads WHERE id=?', (saved['id'],)).fetchone()[0], source)

    def test_concurrent_edit_during_generation_does_not_attach_stale_pdf(self):
        saved = self.save()
        id_ = saved['id']
        def concurrent_conversion(_):
            with database(self.path) as other:
                with other:
                    other.execute('UPDATE document_payloads SET revision=revision+1 WHERE id=?', (id_,))
            return b'%PDF-test'
        with patch('verkuendigungen.api.routes.documents.convert_pdf', side_effect=concurrent_conversion):
            self.assertEqual(self.client.post(f'/api/v1/documents/{id_}/generate?revision=1').status_code, 409)
        self.assertEqual(self.client.get(f'/api/v1/documents/{id_}/pdf').status_code, 404)

    def test_render_keeps_opaque_parts_and_replaces_old_content(self):
        source = Path('resources/vorlage.docx').read_bytes()
        payload = deepcopy(self.payload)
        payload['days'][0]['services'] = [{'id': 'service', 'enabled': True, 'time': '09:15', 'location': {'de': 'Pfarrkirche', 'sl': 'Farna cerkev'}, 'title': {'de': 'Heilige Messe', 'sl': 'Sveta maša'}, 'intentions': [{'id': 'intention', 'enabled': True, 'symbol': '+', 'text': {'de': 'Für die Familie', 'sl': 'Za družino'}, 'reference': '614/25'}], 'notices': []}]
        result = render_docx(source, DocumentPayload.model_validate(payload))
        with ZipFile(BytesIO(source)) as original, ZipFile(BytesIO(result)) as final:
            self.assertEqual(original.namelist(), final.namelist())
            for name in original.namelist():
                if name != 'word/document.xml':
                    self.assertEqual(original.read(name), final.read(name), name)
            root = ET.fromstring(final.read('word/document.xml'))
            text = ''.join(root.itertext())
            for value in ['29.11.2026', '06.12.2026', '09:15', 'Für die Familie', 'Za družino', '614/25']:
                self.assertIn(value, text)
            for stale in ['25.10.2026', '30. SONNTAG IM JAHRESKREIS', 'Gerhard Mischitz', 'eberndorf@']:
                self.assertNotIn(stale, text)

    def test_marker_template_and_unsupported_template(self):
        output = BytesIO()
        with ZipFile(output, 'w') as archive:
            archive.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>{{inhalt}}</w:t></w:r></w:p><w:sectPr /></w:body></w:document>')
        result = render_docx(output.getvalue(), DocumentPayload.model_validate(self.payload))
        with ZipFile(BytesIO(result)) as archive:
            self.assertNotIn(b'{{inhalt}}', archive.read('word/document.xml'))
        bad = BytesIO()
        with ZipFile(bad, 'w') as archive:
            archive.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p /></w:body></w:document>')
        with self.assertRaises(ValueError):
            render_docx(bad.getvalue(), DocumentPayload.model_validate(self.payload))
