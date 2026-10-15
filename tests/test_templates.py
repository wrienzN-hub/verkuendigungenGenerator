import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from fastapi.testclient import TestClient
from verkuendigungen.api.app import create_app


def word_file():
    output = BytesIO()
    with ZipFile(output, 'w') as archive:
        archive.writestr('[Content_Types].xml', '<Types><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml" /></Types>')
        archive.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p /></w:body></w:document>')
    return output.getvalue()


class TemplateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'templates.sqlite3'
        self.client = TestClient(create_app(self.path))
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.temp.cleanup()

    def upload(self, parish='Eberndorf', name='Standard', data=None, filename='vorlage.docx'):
        return self.client.post('/api/v1/templates', data={'parish_name': parish, 'name': name}, files={'file': (filename, word_file() if data is None else data)})

    def test_multiple_parishes_variants_and_original_download(self):
        original = word_file()
        result = self.upload(filename='../Verkündigung.docx', data=original)
        self.assertEqual(result.status_code, 201, result.text)
        template = result.json()
        self.assertEqual(template['source_filename'], 'Verkündigung.docx')
        self.assertNotIn('docx', template)
        self.assertEqual(self.upload('Edling').status_code, 201)
        self.assertEqual(self.upload(name='Feiertage').status_code, 201)
        self.assertEqual(self.upload(' eberndorf ', ' standard ').status_code, 409)
        self.assertEqual(len(self.client.get('/api/v1/templates').json()), 3)
        source = self.client.get(f"/api/v1/templates/{template['id']}/source")
        self.assertEqual(source.content, original)
        self.assertIn('attachment;', source.headers['content-disposition'])
        with TestClient(create_app(self.path)) as reopened:
            self.assertEqual(len(reopened.get('/api/v1/templates').json()), 3)
        self.assertEqual(self.client.get('/api/v1/templates/999/source').status_code, 404)

    def test_invalid_uploads_leave_database_empty(self):
        self.assertEqual(self.upload(filename='test.doc').status_code, 415)
        self.assertEqual(self.upload(data=b'broken').status_code, 422)
        self.assertEqual(self.upload(parish=' ').status_code, 422)
        self.assertEqual(self.upload(name='x' * 121).status_code, 422)
        fake_zip = BytesIO()
        with ZipFile(fake_zip, 'w') as archive:
            archive.writestr('other.txt', 'Not Word')
        self.assertEqual(self.upload(data=fake_zip.getvalue()).status_code, 422)
        with patch('verkuendigungen.api.routes.templates.MAX_UPLOAD_BYTES', 10):
            self.assertEqual(self.upload().status_code, 413)
        self.assertEqual(self.client.get('/api/v1/templates').json(), [])

    def test_existing_reference_word_is_supported(self):
        response = self.upload(data=Path('resources/vorlage.docx').read_bytes())
        self.assertEqual(response.status_code, 201, response.text)
