import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter
from io import BytesIO

from pdf_factory import directorium_pdf
from verkuendigungen.api.app import create_app
from verkuendigungen.infrastructure.database import database, migrate
from verkuendigungen.services.directorium import SOURCE


class UploadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pdf=directorium_pdf()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/'upload.sqlite3'
        self.client=TestClient(create_app(self.path));self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None,None,None);self.temp.cleanup()

    def upload(self,data,filename='directorium.pdf'):
        return self.client.post('/api/v1/imports/directorium',files={'file':(filename,data,'application/pdf')})

    def test_new_year_upload_archive_and_idempotency(self):
        response=self.upload(self.pdf,'../neues-directorium.pdf')
        self.assertEqual(response.status_code,201,response.text)
        result=response.json();self.assertEqual(result['liturgical_year'],'2027/28')
        self.assertEqual(result['calendar_days'],371)
        runs=self.client.get('/api/v1/imports').json()
        self.assertEqual(runs[0]['source_file'],'neues-directorium.pdf')
        self.assertNotIn('source_pdf',runs[0]);self.assertNotIn('status',runs[0])
        archived=self.client.get(f"/api/v1/imports/{result['import_run_id']}/source")
        self.assertEqual(archived.content,self.pdf)
        first=self.client.get('/api/v1/saints?limit=1').json()[0]
        self.client.patch(f"/api/v1/saints/{first['id']}",json={'disabled':True,'name':'Manuell geändert'})
        self.assertEqual(self.upload(self.pdf).status_code,200)
        self.assertEqual(self.client.get(f"/api/v1/saints/{first['id']}").json()['name'],'Manuell geändert')
        self.assertEqual(len(self.client.get('/api/v1/imports').json()),1)
        self.assertNotIn('review_status',first);self.assertNotIn('review_notes',first)

    def test_existing_gurk_pdf_is_uploadable(self):
        result=self.upload(SOURCE.read_bytes())
        self.assertEqual(result.status_code,201,result.text)
        self.assertEqual(result.json()['celebrations'],377)

    def test_changed_file_same_year_is_conflict(self):
        self.assertEqual(self.upload(self.pdf).status_code,201)
        writer=PdfWriter();writer.clone_document_from_reader(PdfReader(BytesIO(self.pdf)))
        writer.add_metadata({'/Title':'Andere Ausgabe'});out=BytesIO();writer.write(out)
        self.assertEqual(self.upload(out.getvalue()).status_code,409)
        self.assertEqual(len(self.client.get('/api/v1/imports').json()),1)

    def test_invalid_and_incomplete_documents_do_not_write_partial_data(self):
        for data in (b'not a pdf',b'%PDF-broken',directorium_pdf(omit='2028-01-01'),directorium_pdf(wrong_weekday=True),directorium_pdf(encrypted=True)):
            with self.subTest(length=len(data)):
                response=self.upload(data)
                self.assertEqual(response.status_code,422,response.text)
                self.assertEqual(self.client.get('/api/v1/imports').json(),[])
                self.assertEqual(self.client.get('/api/v1/saints/page').json()['total'],0)
        self.assertEqual(self.upload(self.pdf,'file.txt').status_code,415)
        with patch('verkuendigungen.api.routes.imports.MAX_UPLOAD_BYTES',64):
            self.assertEqual(self.upload(self.pdf).status_code,413)
        self.assertEqual(self.client.get('/api/v1/imports/99/source').status_code,404)

    def test_review_migration_keeps_ids_and_activation(self):
        legacy=Path(self.temp.name)/'legacy.sqlite3'
        conn=sqlite3.connect(legacy);conn.row_factory=sqlite3.Row
        sql=Path('verkuendigungen/infrastructure/migrations/001_initial.sql').read_text(encoding='utf-8')
        conn.executescript(sql+'\nPRAGMA user_version=1;')
        conn.execute("INSERT INTO import_runs VALUES(1,'old.pdf','hash','2026/27','gurk','v1','2026-01-01','reviewed',?)",(json.dumps({'review_status':'reviewed','warnings':[]}),))
        conn.execute("INSERT INTO calendar_days VALUES(1,1,'2026/27','2026-11-29','So')")
        conn.execute("INSERT INTO source_day_blocks VALUES(1,1,1,'Titel','',1,1,'Original')")
        conn.execute("INSERT INTO saints(id,calendar_day_id,source_block_id,source_key,liturgical_year,celebration_date,name,kind,calendar_scope,observance_status,disabled,source_page,source_reference,source_text) VALUES(42,1,1,'key','2026/27','2026-11-29','Name','saint','DK','observed',1,1,'PDF','Original')")
        conn.commit();migrate(conn)
        self.assertEqual(tuple(conn.execute('SELECT id,name,disabled,source_text FROM saints').fetchone()),(42,'Name',1,'Original'))
        self.assertNotIn('review_status',[r[1] for r in conn.execute('PRAGMA table_info(saints)')])
        self.assertNotIn('review_notes',[r[1] for r in conn.execute('PRAGMA table_info(saints)')])
        self.assertNotIn('status',[r[1] for r in conn.execute('PRAGMA table_info(import_runs)')])
        self.assertEqual(conn.execute('PRAGMA foreign_key_check').fetchall(),[])
        conn.close()
