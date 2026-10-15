import sqlite3
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from verkuendigungen.infrastructure.database import database, migrate
from verkuendigungen.repositories.saints import list_celebrations, set_disabled
from verkuendigungen.services.directorium import celebration_name, import_pdf, parse_block


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
        self.assertEqual({r['name'] for r in rows}, {'Hl. Barbara', 'Hl. Johannes von Damaskus'})
        self.assertEqual({r['rank_code'] for r in rows}, {'g'})
        self.assertEqual(self.entries('2026-12-03')[0]['name'], 'Hl. Franz Xaver')
        self.assertIn('Ordenspriester', self.entries('2026-12-03')[0]['source_text'])

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
        self.assertEqual(self.entries('2027-01-02')[0]['name'], 'Hl. Basilius der Große und hl. Gregor von Nazianz')
        self.assertEqual(self.entries('2027-01-24', True)[0]['name_sl'], '3. NAVADNA NEDELJA')

    def test_migrations_can_be_repeated(self):
        migrate(self.conn)
        self.assertEqual(self.conn.execute('PRAGMA user_version').fetchone()[0], 5)

    def test_older_edition_rank_without_named_commemoration(self):
        block={'date':'2026-02-07','weekday':'Sa','title':'der 4. Woche im Jahreskreis','context':'','lines':[(81,'der 4. Woche im Jahreskreis'),(81,'g Off vom Tag oder vom g')]}
        self.assertEqual(parse_block(block,known_edition=False)[0],[])

    def test_older_pentecost_monday_and_wrapped_suppressed_saints(self):
        block={'date':'2026-05-25','weekday':'Mo','title':'PFINGSTMONTAG','context':'','lines':[(136,line) for line in ['PFINGSTMONTAG','BINKOŠTNI PONEDELJEK','g Maria, Mutter der Kirche','Hl. Beda der Ehrwürdige, Hl. Gregor VII. und Hl.','Maria Magdalena de Pazzi entfallen in diesem Jahr.','Off vom Tag, 4. Woche, oder vom G (Com Maria)']]}
        rows=parse_block(block,known_edition=False)[0]
        self.assertTrue(any(r['name']=='PFINGSTMONTAG' for r in rows))
        suppressed=next(r for r in rows if r['observance_status']=='suppressed')
        self.assertIn('Beda',suppressed['name']);self.assertIn('Maria Magdalena',suppressed['name'])

    def test_name_cleanup_preserves_multiple_saints_and_identifying_aliases(self):
        examples = {
            'Hl. John Fisher, Bischof von Rochester, und hl. Thomas Morus, Lordkanzler, Märtyrer': 'Hl. John Fisher und hl. Thomas Morus',
            'HLL. CYRILL, Mönch, und METHODIUS, Bischof, Schutzpatrone Europas': 'HLL. CYRILL und METHODIUS',
            'Hl. Heinrich II., Kaiser und hl Kunigunde, Kaiserin, (RK)': 'Hl. Heinrich II. und hl Kunigunde',
            'HL. THERESIA BENEDICTA VOM KREUZ (Edith Stein), Jungfrau, Märtyrin': 'HL. THERESIA BENEDICTA VOM KREUZ (Edith Stein)',
            'Hll. Marta, Maria und Lazarus': 'Hll. Marta, Maria und Lazarus',
            'Maria, Mutter der Kirche': 'Maria, Mutter der Kirche',
            'SV. CIRIL, menih, in METOD, škof, zavetnika Evrope': 'SV. CIRIL in METOD',
        }
        for original, expected in examples.items():
            with self.subTest(original=original):
                self.assertEqual(celebration_name(original), expected)
                self.assertEqual(celebration_name(expected), expected)

    def test_existing_import_gets_clean_names_without_losing_source_or_status(self):
        row = self.entries('2026-12-04')[0]
        with self.conn:
            self.conn.execute('UPDATE saints SET name=?,disabled=1 WHERE id=?', (row['source_text'], row['id']))
            self.conn.execute("UPDATE import_runs SET parser_version='gurk-2026-27-v1'")
        try:
            report = import_pdf(self.conn)
            updated = next(r for r in self.entries('2026-12-04') if r['id'] == row['id'])
            self.assertEqual(report['updated_names'], 1)
            self.assertEqual(updated['name'], row['name'])
            self.assertEqual(updated['source_text'], row['source_text'])
            self.assertEqual(updated['disabled'], 1)
            self.assertEqual(import_pdf(self.conn)['updated_names'], 0)
        finally:
            set_disabled(self.conn, row['id'], False)


if __name__ == '__main__':
    unittest.main()
