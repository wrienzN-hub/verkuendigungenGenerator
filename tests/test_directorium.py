import sqlite3
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from verkuendigungen.infrastructure.database import database, migrate
from verkuendigungen.repositories.saints import list_celebrations, set_disabled
from verkuendigungen.services.directorium import import_pdf


class DirectoriumImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.manager = database(Path(cls.temp.name) / 'test.sqlite3')
        cls.conn = cls.manager.__enter__()
        cls.report = import_pdf(cls.conn)

    @classmethod
    def tearDownClass(cls):
        cls.manager.__exit__(None, None, None)
        cls.temp.cleanup()

    def entries(self, day, available=False):
        return list_celebrations(self.conn, day, day, available_only=available)

    def test_complete_year_with_both_october_25_variants(self):
        dates = [r[0] for r in self.conn.execute('SELECT calendar_date FROM calendar_days ORDER BY calendar_date')]
        expected = [(date(2026, 11, 29) + timedelta(days=i)).isoformat() for i in range(364)]
        self.assertEqual(dates, expected)
        self.assertEqual(self.conn.execute('SELECT count(*) FROM source_day_blocks').fetchone()[0], 365)
        self.assertEqual(self.conn.execute('SELECT count(*) FROM source_pages').fetchone()[0], 227)
        self.assertEqual(self.conn.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
        self.assertEqual(self.conn.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_suppressed_nicholas_not_available(self):
        self.assertTrue(any(r['name'] == 'Hl. Nikolaus' and r['observance_status'] == 'suppressed' for r in self.entries('2026-12-06')))
        self.assertFalse(any('Nikolaus' in r['name'] for r in self.entries('2026-12-06', True)))
        self.assertEqual(self.entries('2026-12-06', True)[0]['name_sl'], '2. ADVENTNA NEDELJA')

    def test_multiple_optional_saints_and_wrapped_title(self):
        rows = self.entries('2026-12-04', True)
        self.assertEqual({r['name'] for r in rows}, {'Hl. Barbara, Märtyrin in Nikomedien (RK)', 'Hl. Johannes von Damaskus, Priester, Kirchenlehrer'})
        self.assertEqual({r['rank_code'] for r in rows}, {'g'})
        self.assertEqual(self.entries('2026-12-03')[0]['name'], 'Hl. Franz Xaver, Ordenspriester, Glaubensbote in Indien und Ostasien')

    def test_christmas_and_lenten_commemorations(self):
        self.assertEqual(next(r for r in self.entries('2026-12-29') if 'Becket' in r['name'])['observance_status'], 'commemoration_only')
        self.assertEqual(self.entries('2027-02-23')[0]['observance_status'], 'commemoration_only')
        self.assertTrue(any(r['name'].startswith('ASCHERMITTWOCH') for r in self.entries('2027-02-10', True)))
        self.assertFalse(any('Scholastika' in r['name'] for r in self.entries('2027-02-10', True)))

    def test_local_conditions_require_explicit_selection(self):
        self.assertEqual(self.entries('2027-10-25', True), [])
        self.assertEqual(self.entries('2027-10-25')[0]['observance_status'], 'conditional')
        self.assertEqual(len(self.entries('2027-09-19', True)), 1)

    def test_dates_follow_daily_sections_not_inconsistent_year_overview(self):
        self.assertTrue(any('FRONLEICHNAM' in r['name'] for r in self.entries('2027-05-27', True)))
        self.assertTrue(any('HERZ JESU' in r['name'] for r in self.entries('2027-06-04', True)))
        self.assertTrue(any('VERKÜNDIGUNG' in r['name'] for r in self.entries('2027-04-05', True)))

    def test_reimport_preserves_ids_and_disabled_state(self):
        saint_id = self.entries('2026-12-04')[0]['id']
        set_disabled(self.conn, saint_id, True)
        try:
            report = import_pdf(self.conn)
            self.assertTrue(report['already_imported'])
            self.assertEqual(self.conn.execute('SELECT count(*) FROM import_runs').fetchone()[0], 1)
            self.assertTrue(next(r for r in self.entries('2026-12-04') if r['id'] == saint_id)['disabled'])
            self.assertFalse(any(r['id'] == saint_id for r in self.entries('2026-12-04', True)))
        finally:
            set_disabled(self.conn, saint_id, False)

    def test_invalid_mutations_and_ranges(self):
        with self.assertRaises(ValueError):
            set_disabled(self.conn, -1, True)
        with self.assertRaises(ValueError):
            list_celebrations(self.conn, '2027-02-30', '2027-03-01')
        with self.assertRaises(ValueError):
            list_celebrations(self.conn, '2027-03-02', '2027-03-01')
        with self.assertRaises(sqlite3.IntegrityError), self.conn:
            self.conn.execute('UPDATE saints SET disabled=2 WHERE id=1')

    def test_titles_do_not_include_wrapped_prayer_notes(self):
        self.assertEqual(self.entries('2027-01-02')[0]['name'], 'Hl. Basilius der Große und hl. Gregor von Nazianz, Bischöfe, Kirchenlehrer')
        self.assertEqual(self.entries('2027-01-24', True)[0]['name_sl'], '3. NAVADNA NEDELJA')

    def test_migrations_can_be_repeated(self):
        migrate(self.conn)
        self.assertEqual(self.conn.execute('PRAGMA user_version').fetchone()[0], 1)


if __name__ == '__main__':
    unittest.main()
