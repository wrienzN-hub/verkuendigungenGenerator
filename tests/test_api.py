import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from verkuendigungen.api.app import create_app
from verkuendigungen.infrastructure.database import database
from verkuendigungen.services.directorium import import_pdf


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.temp.name) / 'api.sqlite3'
        with database(cls.path) as conn:
            import_pdf(conn)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.client = TestClient(create_app(self.path))
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def test_health_and_openapi(self):
        self.assertEqual(self.client.get('/health').json(), {'status': 'ok'})
        self.assertIn('/api/v1/saints/{saint_id}', self.client.get('/openapi.json').json()['paths'])

    def test_week_filter_and_boolean_serialization(self):
        response = self.client.get('/api/v1/saints', params={'start': '2026-11-29', 'end': '2026-12-06', 'available_only': True})
        self.assertEqual(response.status_code, 200)
        rows = response.json()
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(r['disabled'] is False for r in rows))
        self.assertFalse(any('Nikolaus' in r['name'] for r in rows))

    def test_admin_search_and_pagination(self):
        rows = self.client.get('/api/v1/saints', params={'search': 'Nikolaus', 'year': '2026/27'}).json()
        self.assertEqual(rows[0]['observance_status'], 'suppressed')
        first = self.client.get('/api/v1/saints', params={'limit': 1}).json()
        second = self.client.get('/api/v1/saints', params={'limit': 1, 'offset': 1}).json()
        self.assertNotEqual(first[0]['id'], second[0]['id'])

    def test_patch_persists_and_rejects_non_booleans(self):
        url = '/api/v1/saints/1'
        try:
            response = self.client.patch(url, json={'disabled': True})
            self.assertEqual(response.status_code, 200)
            self.assertIs(response.json()['disabled'], True)
            self.assertIs(self.client.get(url).json()['disabled'], True)
            self.assertEqual(self.client.patch(url, json={'disabled': 1}).status_code, 422)
            self.assertEqual(self.client.patch(url, json={'disabled': False, 'source_text': 'x'}).status_code, 422)
        finally:
            self.client.patch(url, json={'disabled': False})

    def test_invalid_dates_and_missing_records(self):
        self.assertEqual(self.client.get('/api/v1/saints?start=2027-02-30').status_code, 422)
        self.assertEqual(self.client.get('/api/v1/saints?start=2027-03-02&end=2027-03-01').status_code, 422)
        self.assertEqual(self.client.get('/api/v1/saints?limit=0').status_code, 422)
        self.assertEqual(self.client.get('/api/v1/saints/99999').status_code, 404)
        self.assertEqual(self.client.patch('/api/v1/saints/99999', json={'disabled': False}).status_code, 404)

    def test_import_status(self):
        response = self.client.get('/api/v1/imports')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]['report']['celebrations'], 377)

    def test_filtered_paging_returns_matching_count(self):
        response=self.client.get('/api/v1/saints/page',params={'month':12,'rank':'g','limit':2})
        self.assertEqual(response.status_code,200)
        data=response.json()
        self.assertEqual(len(data['items']),2)
        self.assertGreater(data['total'],2)
        self.assertTrue(all(r['rank_code']=='g' and r['celebration_date'][5:7]=='12' for r in data['items']))
        self.assertEqual(self.client.get('/api/v1/saints/page?month=13').status_code,422)
        self.assertEqual(self.client.get('/api/v1/saints/page?rank=invalid').status_code,422)
        self.assertEqual(self.client.get('/api/v1/saints/filters').json()['years'],['2026/27'])

    def test_editable_fields_preserve_source_and_reject_invalid_patches(self):
        url='/api/v1/saints/1'
        original=self.client.get(url).json()
        changes={'name':'Neuer Name','name_sl':'Slovensko ime','rank_code':'F','observance_status':'conditional','applicability_note':'Nur örtlich'}
        try:
            result=self.client.patch(url,json=changes)
            self.assertEqual(result.status_code,200)
            for key,value in changes.items(): self.assertEqual(result.json()[key],value)
            self.assertEqual(result.json()['source_text'],original['source_text'])
            for bad in ({'name':'  '},{'name':None},{'disabled':None},{'rank_code':'X'},{}, {'review_status':'reviewed'}, {'review_notes':'x'}):
                self.assertEqual(self.client.patch(url,json=bad).status_code,422,bad)
        finally:
            self.client.patch(url,json={key:original[key] for key in changes})

    def test_unicode_search_and_disable_filter(self):
        rows=self.client.get('/api/v1/saints/page',params={'search':'ÄMILIANI'}).json()['items']
        self.assertEqual(len(rows),1)
        self.assertIn('Ämiliani',rows[0]['name'])
        self.assertEqual(self.client.get('/api/v1/saints/page?search=not-a-saint-xyz').json()['total'],0)
