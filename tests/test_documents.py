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
                    self.assertTrue(celebration['enabled'])
        weeks = self.client.get('/api/v1/documents/weeks?year=2026%2F27').json()
        self.assertEqual(weeks[0]['start'], '2026-11-29')
        self.assertEqual(self.client.post('/api/v1/documents/prepare', json={'template_id': 0, 'year': '2026/27', 'week_id': 'invalid'}).status_code, 422)

    def test_save_reopen_snapshot_revision_and_word_invalidation(self):
        saved = self.save()
        id_ = saved['id']
        self.assertEqual(self.client.get(f'/api/v1/documents/{id_}').json()['payload'], saved['payload'])
        with patch('verkuendigungen.api.routes.documents.convert_pdf', return_value=b'%PDF-test'):
            self.assertEqual(self.client.post(f'/api/v1/documents/{id_}/preview?revision=1').status_code, 200)
        self.assertEqual(self.client.get(f'/api/v1/documents/{id_}/preview?revision=1').content, b'%PDF-test')
        word = self.client.get(f'/api/v1/documents/{id_}/docx')
        with ZipFile(BytesIO(word.content)) as archive:
            self.assertIn('word/document.xml', archive.namelist())
        payload = deepcopy(saved['payload'])
        payload['days'][0]['celebrations'][0]['title']['de'] = 'Manuell geändert'
        updated = self.client.put(f'/api/v1/documents/{id_}', json={'payload': payload, 'revision': 1})
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()['revision'], 2)
        self.assertFalse(updated.json()['has_pdf'])
        self.assertFalse(updated.json()['has_docx'])
        self.assertEqual(self.client.get(f'/api/v1/documents/{id_}/preview?revision=1').status_code, 409)
        self.assertEqual(self.client.get(f'/api/v1/documents/{id_}/docx').status_code, 404)
        self.assertEqual(self.client.put(f'/api/v1/documents/{id_}', json={'payload': payload, 'revision': 1}).status_code, 409)
        self.assertEqual(self.client.post(f'/api/v1/documents/{id_}/generate?revision=1').status_code, 409)
        with patch('verkuendigungen.api.routes.documents.convert_pdf', side_effect=ConversionError('Konvertierung fehlt')):
            self.assertEqual(self.client.post(f'/api/v1/documents/{id_}/preview?revision=2').status_code, 503)
        with patch('verkuendigungen.api.routes.documents.convert_pdf', side_effect=ConversionError('Kein Konverter')) as converter:
            self.assertEqual(self.client.post(f'/api/v1/documents/{id_}/generate?revision=2').status_code, 200)
            converter.assert_not_called()
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
            self.assertEqual(self.client.post(f'/api/v1/documents/{id_}/preview?revision=1').status_code, 409)
        self.assertEqual(self.client.get(f'/api/v1/documents/{id_}/docx').status_code, 404)

    def test_parish_defaults_apply_to_both_sundays_with_unique_ids_and_snapshot(self):
        defaults = {'services': [{'id': 'sunday', 'weekday': 6, 'time': '09:15', 'title': {'de': 'Heilige Messe'}, 'location': {'de': 'Pfarrkirche'}}, {'id': 'disabled', 'weekday': 0, 'enabled': False, 'time': '18:00'}], 'contact': {'email': 'pfarre@example.org'}}
        result = self.client.put('/api/v1/settings?parish=Eberndorf', json=defaults)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(self.client.get('/api/v1/settings?parish=eberndorf').json()['services'][0]['time'], '09:15')
        self.assertEqual(self.client.get('/api/v1/settings?parish=Edling').json()['services'], [])
        payload = self.client.post('/api/v1/documents/prepare', json={'template_id': 0, 'year': '2026/27', 'week_id': 'advent:2026-11-29'}).json()['payload']
        self.assertEqual([len(day['services']) for day in payload['days']], [1, 0, 0, 0, 0, 0, 0, 1])
        self.assertNotEqual(payload['days'][0]['services'][0]['id'], payload['days'][7]['services'][0]['id'])
        self.assertEqual(payload['contact']['email'], 'pfarre@example.org')
        saved = self.save(payload)
        self.client.put('/api/v1/settings?parish=Eberndorf', json={'services': []})
        self.assertEqual(self.client.get(f"/api/v1/documents/{saved['id']}").json()['payload'], saved['payload'])

    def test_invalid_default_times_and_weekdays_do_not_overwrite_settings(self):
        for rule in [{'id': 'rule', 'weekday': 7}, {'id': 'rule', 'weekday': 0, 'time': '25:00'}, {'id': 'rule', 'weekday': 0, 'enabled': 'yes'}]:
            response = self.client.put('/api/v1/settings?parish=Eberndorf', json={'services': [rule]})
            self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.client.get('/api/v1/settings?parish=Eberndorf').json()['services'], [])

    def test_delete_removes_payload_and_outputs_but_preserves_templates(self):
        saved = self.save()
        id_ = saved['id']
        self.client.post(f'/api/v1/documents/{id_}/generate?revision=1')
        self.assertEqual(self.client.delete(f'/api/v1/documents/{id_}?revision=2').status_code, 409)
        self.assertEqual(self.client.get(f'/api/v1/documents/{id_}/docx').status_code, 200)
        self.assertEqual(self.client.delete(f'/api/v1/documents/{id_}?revision=1').status_code, 200)
        self.assertEqual(self.client.get(f'/api/v1/documents/{id_}').status_code, 404)
        self.assertEqual(self.client.get(f'/api/v1/documents/{id_}/docx').status_code, 404)
        self.assertEqual(self.client.get('/api/v1/documents').json()['total'], 0)
        self.assertTrue(self.client.get('/api/v1/documents/options').json()['templates'])

    def test_rich_word_runs_and_normal_eternal_light_names(self):
        payload = deepcopy(self.payload)
        text = '🙏 Bitte Anmeldung bis Freitag'
        start = text.index('Anmeldung')
        payload['days'][0]['notices'] = [{'id': 'rich-notice', 'enabled': True, 'text': {'de': text, 'sl': '', 'de_marks': [{'start': start, 'end': start + len('Anmeldung'), 'bold': True}]}}]
        payload['eternal_light']['dedication'] = {'de': 'Sowak Edi und Angehörige', 'sl': ''}
        payload['announcements'] = [{'id': 'rich-announcement', 'enabled': True, 'title': {'de': 'Anmeldung zur Firmung', 'sl': ''}, 'paragraphs': [{'de': 'Informationen auf www.example.org', 'de_marks': [{'start': 17, 'end': 32, 'bold': True}]}]}]
        parsed = DocumentPayload.model_validate(payload)
        data = render_docx(Path('resources/vorlage.docx').read_bytes(), parsed)
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        with ZipFile(BytesIO(data)) as archive:
            root = ET.fromstring(archive.read('word/document.xml'))
            runs = [(''.join(run.xpath('.//w:t/text()', namespaces=ns)), run.find('w:rPr/w:b', ns)) for run in root.findall('.//w:r', ns)]
            selected = next(weight for text, weight in runs if text == 'Anmeldung')
            self.assertEqual(selected.get('{'+ns['w']+'}val'), '1')
            names = next(weight for text, weight in runs if 'Sowak Edi' in text)
            self.assertEqual(names.get('{'+ns['w']+'}val'), '0')
            label = next(weight for text, weight in runs if text.startswith('Das ewige Licht'))
            self.assertEqual(label.get('{'+ns['w']+'}val'), '1')
        saved = self.save(parsed.model_dump(mode='json', by_alias=True))
        self.assertEqual(saved['payload']['days'][0]['notices'][0]['text']['de_marks'][0]['start'], start)

    def test_shared_sunday_services_and_conflicts(self):
        payload = deepcopy(self.payload)
        payload['days'][7]['services'] = [{'id': 'shared-service', 'time': '09:15', 'title': {'de': 'Heilige Messe'}, 'intentions': [{'id': 'shared-intention', 'text': {'de': 'Fuer die Familie'}}]}]
        saved = self.save(payload)
        next_payload = self.client.post('/api/v1/documents/prepare', json={'template_id': 0, 'year': '2026/27', 'week_id': 'advent:2026-12-06'}).json()['payload']
        self.assertEqual(next_payload['days'][0]['services'], saved['payload']['days'][7]['services'])
        self.assertEqual(next_payload['days'][0]['services'][0]['title']['de'], '')
        self.assertEqual(next_payload['days'][7]['services'], [])
        read = self.client.get('/api/v1/services/2026-12-06?parish=Eberndorf').json()
        edited = deepcopy(read)
        edited['services'][0]['intentions'][0]['text']['de'] = 'Geaendert'
        updated = self.client.put('/api/v1/services/2026-12-06?parish=Eberndorf', json=edited)
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(self.client.put('/api/v1/services/2026-12-06?parish=Eberndorf', json=read).status_code, 409)
        stale = deepcopy(next_payload)
        stale['days'][0]['services'][0]['time'] = '10:00'
        self.assertEqual(self.client.post('/api/v1/documents', json={'payload': stale}).status_code, 409)
        self.assertEqual(self.client.get('/api/v1/services/2026-12-06?parish=Edling').json()['services'], [])
        snapshot = self.client.get(f"/api/v1/documents/{saved['id']}").json()['payload']
        self.assertEqual(snapshot['days'][7]['services'][0]['intentions'][0]['text']['de'], 'Fuer die Familie')
        unchanged = self.client.put(f"/api/v1/documents/{saved['id']}", json={'payload': snapshot, 'revision': saved['revision']})
        self.assertEqual(unchanged.status_code, 200, unchanged.text)
        self.assertEqual(self.client.get('/api/v1/services/2026-12-06?parish=Eberndorf').json()['services'][0]['intentions'][0]['text']['de'], 'Geaendert')
        self.client.put('/api/v1/settings?parish=Eberndorf', json={'services': [{'id': 'weekly', 'weekday': 6, 'time': '09:15'}]})
        removed = self.client.put('/api/v1/services/2026-12-06?parish=Eberndorf', json={'services': [], 'revision': updated.json()['revision']})
        self.assertEqual(removed.status_code, 200)
        next_payload = self.client.post('/api/v1/documents/prepare', json={'template_id': 0, 'year': '2026/27', 'week_id': 'advent:2026-12-06'}).json()['payload']
        self.assertEqual(next_payload['days'][0]['services'], [])

    def test_underline_and_office_hours_word_output(self):
        payload = deepcopy(self.payload)
        payload['announcements'] = [{'id': 'underlined', 'paragraphs': [{'de': 'Anmeldung normal', 'de_marks': [{'start': 0, 'end': 9, 'bold': True, 'underline': True}]}]}]
        payload['office_hours'] = [{'weekday': 'tuesday', 'from': '09:00', 'until': '12:00'}, {'weekday': 'thursday', 'from': '10:00', 'until': '12:00'}]
        payload['days'][0]['services'] = [{'id': 'old-title', 'title': {'de': 'DO NOT PRINT', 'sl': 'NO TITLE'}}]
        data = render_docx(Path('resources/vorlage.docx').read_bytes(), DocumentPayload.model_validate(payload))
        with ZipFile(BytesIO(data)) as archive:
            root = ET.fromstring(archive.read('word/document.xml'))
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        run = next(r for r in root.findall('.//w:r', ns) if ''.join(r.itertext()) == 'Anmeldung')
        self.assertEqual(run.find('w:rPr/w:u', ns).get('{'+ns['w']+'}val'), 'single')
        self.assertEqual(run.find('w:rPr/w:b', ns).get('{'+ns['w']+'}val'), '1')
        text = ''.join(root.itertext())
        self.assertNotIn('DO NOT PRINT', text)
        self.assertNotIn('NO TITLE', text)
        self.assertIn('09:00', text)
        for p in root.findall('.//w:p', ns):
            if '09:00' in ''.join(p.itertext()):
                self.assertNotIn('Kanzleistunden', ''.join(p.itertext()))

    def test_invalid_rich_text_ranges_are_rejected(self):
        for marks in [[{'start': 0, 'end': 99, 'bold': True}], [{'start': 2, 'end': 1, 'bold': True}], [{'start': 0, 'end': 3, 'bold': True}, {'start': 2, 'end': 4, 'bold': False}]]:
            payload = deepcopy(self.payload)
            payload['days'][0]['notices'] = [{'id': 'invalid', 'text': {'de': 'Text', 'de_marks': marks}}]
            self.assertEqual(self.client.post('/api/v1/documents', json={'payload': payload}).status_code, 422)

    def test_events_crud_week_filter_paging_and_snapshot(self):
        week = {'year': '2026/27', 'week_id': 'advent:2026-11-29'}
        second = {'year': '2026/27', 'week_id': 'advent:2026-12-06'}
        body = {'name': 'Firmvorbereitungen intern', 'parishes': ['Eberndorf', 'Edling'], 'weeks': [week, second], 'text': {'de': 'Alle sind eingeladen', 'de_marks': [{'start': 0, 'end': 4, 'bold': True}]}}
        created = self.client.post('/api/v1/events', json=body)
        self.assertEqual(created.status_code, 201, created.text)
        event = created.json(); id_ = event['id']
        self.client.post('/api/v1/events', json={**body, 'name': 'Entwurf', 'weeks': []})
        self.client.post('/api/v1/events', json={**body, 'name': 'Nur Edling', 'parishes': ['Edling']})
        matching = self.client.get('/api/v1/events?parish=Edling&year=2026/27&week_id=advent:2026-11-29&limit=1&offset=1').json()
        self.assertEqual(matching['total'], 2)
        self.assertEqual(len(matching['items']), 1)
        self.assertEqual(self.client.get('/api/v1/events?search=FIRM').json()['total'], 1)
        for selected in [week, second]:
            prepared = self.client.post('/api/v1/documents/prepare', json={'template_id': 0, 'year': selected['year'], 'week_id': selected['week_id']}).json()['payload']
            self.assertEqual(len(prepared['announcements']), 1)
            self.assertEqual(prepared['announcements'][0]['title']['de'], '')
            self.assertEqual(prepared['announcements'][0]['paragraphs'][0], event['text'])
        unassigned = self.client.post('/api/v1/documents/prepare', json={'template_id': 0, 'year': '2026/27', 'week_id': 'advent:2026-12-13'}).json()['payload']
        self.assertEqual(unassigned['announcements'], [])
        uploaded = self.client.post('/api/v1/templates', data={'parish_name': 'Edling', 'name': 'Test'}, files={'file': ('test.docx', Path('resources/vorlage.docx').read_bytes())}).json()
        prepared = self.client.post('/api/v1/documents/prepare', json={'template_id': uploaded['id'], 'year': week['year'], 'week_id': week['week_id']}).json()['payload']
        self.assertEqual(len(prepared['announcements']), 2)
        rendered = render_docx(Path('resources/vorlage.docx').read_bytes(), DocumentPayload.model_validate(prepared))
        with ZipFile(BytesIO(rendered)) as archive:
            xml = archive.read('word/document.xml').decode('utf-8')
        self.assertIn('Alle', xml)
        self.assertNotIn('Firmvorbereitungen intern', xml)
        invalid = [dict(body, parishes=[]), dict(body, name=' '), dict(body, weeks=[week, week]), dict(body, weeks=[dict(week, week_id='invalid')]), dict(body, event_date='2026-12-01')]
        for entry in invalid:
            self.assertEqual(self.client.post('/api/v1/events', json=entry).status_code, 422)
        self.assertEqual(self.client.put(f'/api/v1/events/{id_}', json={**body, 'revision': 99}).status_code, 409)
        payload = deepcopy(self.payload)
        payload['days'][0]['notices'] = [{'id': 'event-copy', 'enabled': True, 'source_event_id': id_, 'text': event['text']}]
        saved = self.save(payload)
        updated = self.client.put(f'/api/v1/events/{id_}', json={**body, 'text': {'de': 'Geändert'}, 'revision': 1})
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(self.client.delete(f'/api/v1/events/{id_}?revision=1').status_code, 409)
        self.assertEqual(self.client.delete(f'/api/v1/events/{id_}?revision=2').status_code, 200)
        self.assertEqual(self.client.get(f'/api/v1/events/{id_}').status_code, 404)
        snapshot = self.client.get(f"/api/v1/documents/{saved['id']}").json()['payload']['days'][0]['notices'][0]
        self.assertEqual(snapshot['text']['de'], 'Alle sind eingeladen')
        self.assertEqual(snapshot['text']['de_marks'], [{'start': 0, 'end': 4, 'bold': True, 'underline': False}])
        newest = self.client.post('/api/v1/events', json=body).json()
        self.client.delete(f"/api/v1/events/{newest['id']}?revision=1")
        replacement = self.client.post('/api/v1/events', json=body).json()
        self.assertGreater(replacement['id'], newest['id'])

    def test_optional_saint_day_and_multiple_bold_bilingual_titles(self):
        payload = deepcopy(self.payload)
        for index, (de, sl) in enumerate([('Kirchtag Hl. Lukas', 'Žegnanje Sv. Luka'), ('Erntedank', 'Zahvalna maša')]):
            payload['days'][0]['celebrations'].append({'id': f'manual-title-{index}', 'enabled': True, 'source_celebration_id': None, 'title': {'de': de, 'sl': sl}, 'rank': None})
        result = render_docx(Path('resources/vorlage.docx').read_bytes(), DocumentPayload.model_validate(payload))
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        with ZipFile(BytesIO(result)) as archive:
            root = ET.fromstring(archive.read('word/document.xml'))
            text = ''.join(root.itertext())
            self.assertIn('02.12.2026', text)
            for title in ['Kirchtag Hl. Lukas | Žegnanje Sv. Luka', 'Erntedank | Zahvalna maša']:
                paragraph = next(p for p in root.findall('.//w:p', ns) if ''.join(p.itertext()) == title)
                self.assertEqual(paragraph.find('w:r/w:rPr/w:b', ns).get('{'+ns['w']+'}val'), '1')

    def test_empty_days_are_printed_unless_explicitly_disabled(self):
        payload = deepcopy(self.payload)
        for day in payload['days']:
            day['celebrations'] = []
            day['services'] = []
            day['notices'] = []
        payload['days'][3]['enabled'] = False
        saved = self.save(payload)
        response = self.client.post(f"/api/v1/documents/{saved['id']}/generate?revision=1")
        self.assertEqual(response.status_code, 200, response.text)
        data = self.client.get(f"/api/v1/documents/{saved['id']}/docx").content
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        with ZipFile(BytesIO(data)) as archive:
            root = ET.fromstring(archive.read('word/document.xml'))
            text = ''.join(root.itertext())
            for index, day in enumerate(payload['days']):
                formatted = __import__('datetime').date.fromisoformat(day['date']).strftime('%d.%m.%Y')
                if index == 3:
                    self.assertNotIn(formatted, text)
                else:
                    self.assertIn(formatted, text)
            self.assertEqual(len(root.findall('w:body/w:tbl/w:tr', ns)), 7)

    def test_legacy_overlaid_banner_is_normalized_without_changing_original_parts(self):
        source = Path('resources/vorlage.docx').read_bytes()
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main', 'v': 'urn:schemas-microsoft-com:vml'}
        with ZipFile(BytesIO(source)) as original:
            root = ET.fromstring(original.read('word/document.xml'))
            body = root.find('w:body', ns)
            banner = body[0]
            existing = banner.find('.//w:pict', ns)
            inner = deepcopy(existing)
            inner.find('v:shape', ns).set('style', 'width:574pt;height:78pt')
            banner.clear()
            outer = ET.SubElement(ET.SubElement(banner, '{'+ns['w']+'}r'), '{'+ns['w']+'}pict')
            shape = ET.SubElement(outer, '{'+ns['v']+'}shape')
            box = ET.SubElement(ET.SubElement(shape, '{'+ns['v']+'}textbox'), '{'+ns['w']+'}txbxContent')
            ET.SubElement(ET.SubElement(box, '{'+ns['w']+'}p'), '{'+ns['w']+'}r').append(inner)
            peer = deepcopy(inner)
            ET.SubElement(ET.SubElement(box, '{'+ns['w']+'}p'), '{'+ns['w']+'}r').append(peer)
            out = BytesIO()
            with ZipFile(out, 'w') as changed:
                for item in original.infolist():
                    changed.writestr(item, ET.tostring(root) if item.filename == 'word/document.xml' else original.read(item.filename))
        result = render_docx(out.getvalue(), DocumentPayload.model_validate(self.payload))
        with ZipFile(BytesIO(result)) as final, ZipFile(BytesIO(source)) as original:
            root = ET.fromstring(final.read('word/document.xml'))
            self.assertEqual(len(root.findall('.//w:pict', ns)), 1)
            for name in original.namelist():
                if name != 'word/document.xml':
                    self.assertEqual(final.read(name), original.read(name))

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
