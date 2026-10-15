import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from verkuendigungen.api.app import create_app
from verkuendigungen.infrastructure.database import database
from verkuendigungen.services.directorium import import_pdf
from verkuendigungen.services.liturgical_weeks import list_weeks


class LiturgicalWeekTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.temp.name) / 'weeks.sqlite3'
        with database(cls.path) as conn:
            import_pdf(conn)
        cls.client = TestClient(create_app(cls.path))
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None,None,None)
        cls.temp.cleanup()

    def test_source_week_dates_across_seasons(self):
        with database(self.path) as conn:
            weeks = list_weeks(conn,'2026/27')
        for season, number, start, end in [
            ('advent',1,'2026-11-29','2026-12-06'),
            ('advent',4,'2026-12-20','2026-12-27'),
            ('lent',1,'2027-02-14','2027-02-21'),
            ('holy_week',None,'2027-03-21','2027-03-28'),
            ('easter',1,'2027-03-28','2027-04-04'),
            ('ordinary_time',1,'2027-01-10','2027-01-17'),
        ]:
            with self.subTest(season=season,number=number):
                week=next(w for w in weeks if w['season']==season and w['week']==number)
                self.assertEqual((week['start'],week['end']),(start,end))
        self.assertTrue(any(w['season']=='christmas' for w in weeks))
        self.assertEqual(len({w['id'] for w in weeks}),len(weeks))

    def test_filter_includes_both_sundays_and_correct_total(self):
        params={'year':'2026/27','liturgical_week':'advent:2026-11-29'}
        response=self.client.get('/api/v1/saints/page',params=params)
        self.assertEqual(response.status_code,200)
        data=response.json()
        self.assertEqual(data['total'],9)  # einschließlich des entfallenen Nikolaus.
        self.assertEqual(data['items'][0]['celebration_date'],'2026-11-29')
        self.assertEqual(data['items'][-1]['celebration_date'],'2026-12-06')
        page=self.client.get('/api/v1/saints/page',params={**params,'limit':2,'offset':2}).json()
        self.assertEqual(page['total'],data['total'])
        self.assertEqual(len(page['items']),2)
        result=self.client.get('/api/v1/saints/page',params={**params,'search':'Barbara'}).json()
        self.assertEqual(result['total'],1)

    def test_invalid_selection_and_unknown_year(self):
        self.assertEqual(self.client.get('/api/v1/saints/weeks?year=2090/91').json(),[])
        self.assertEqual(self.client.get('/api/v1/saints/page?liturgical_week=advent:2026-11-29').status_code,422)
        self.assertEqual(self.client.get('/api/v1/saints/page?year=2026/27&liturgical_week=advent:2026-11-30').status_code,422)
        result=self.client.get('/api/v1/saints/page',params={'year':'2026/27','liturgical_week':'advent:2026-11-29','start':'2027-01-01'}).json()
        self.assertEqual(result['total'],0)
