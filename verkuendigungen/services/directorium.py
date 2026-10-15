"""Nachvollziehbarer Import der vorhandenen Directorium-Ausgabe 2026/27.

Die Extraktion ist bewusst editionsgebunden. Abweichende Kalenderstrukturen
werden nicht stillschweigend mit denselben Annahmen interpretiert.
"""

import hashlib
import json
import re
import unicodedata
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from pypdf import PdfReader

from ..core.config import ROOT
from ..infrastructure.database import migrate

SOURCE = ROOT / "resources/directorium-2026-27-kern_21092026.pdf"
PARSER_VERSION = "gurk-2026-27-v1"
SOURCE_SHA256 = 'e44ce1c4b155a77ca6f36b1ae0c5d8f4495c4e3207a63ce0ab84d1a12b761f4a'
YEAR = "2026/27"
START, END = date(2026, 11, 29), date(2027, 11, 27)
MONTHS = {
    "NOVEMBER": 11, "DEZEMBER": 12, "JÄNNER": 1, "FEBER": 2,
    "MÄRZ": 3, "APRIL": 4, "MAI": 5, "JUNI": 6, "JULI": 7,
    "AUGUST": 8, "SEPTEMBER": 9, "OKTOBER": 10,
}
DAY = re.compile(r"^(\d{1,2})\s+(Mo|Di|Mi|Do|Fr|Sa|So)\s+(.+)$")
MONTH = re.compile(r"^(" + "|".join(MONTHS) + r")\s+(2026|2027)$")
RANK = re.compile(r"^([HFGg])(?:\s+(.*))?$")
SUPPRESSED = re.compile(r"(.+?)\s+entf(?:ällt|allen)\s+in diesem Jahr\.", re.I)
WEEKDAYS = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']


def clean(value):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value)).strip()


def join_lines(lines):
    # Ein echter Bindestrich am Zeilenende wird bei Worttrennung aufgelöst.
    return clean(re.sub(r"-\n(?=[a-zäöüßčšž])", "", "\n".join(lines)))


def extract_blocks(pages):
    blocks, current = [], None
    for page_num, text in enumerate(pages, 1):
        # Nur das eigentliche Kalendarium, nicht Einleitung oder Jahrestafel.
        if not 54 <= page_num <= 225:
            continue
        month_matches = [MONTH.fullmatch(line.strip()) for line in text.splitlines()]
        month_match = next((m for m in month_matches if m), None)
        if month_match is None:
            raise ValueError(f"Monatsüberschrift auf PDF-Seite {page_num} fehlt.")
        month, year = MONTHS[month_match[1]], int(month_match[2])
        lines = text.splitlines()
        for index, raw_line in enumerate(lines):
            line = clean(raw_line)
            if not line or line.isdigit() or MONTH.fullmatch(line):
                continue
            match = DAY.fullmatch(line)
            if match:
                day_date = date(year, month, int(match[1]))
                if not START <= day_date <= END:
                    raise ValueError(f"Datum außerhalb des Kirchenjahres: {day_date}")
                if WEEKDAYS[day_date.weekday()] != match[2]:
                    raise ValueError(f"Wochentag stimmt nicht: {day_date} ({match[2]})")
                if current:
                    blocks.append(current)
                context = " ".join(clean(x) for x in lines[max(0, index-3):index])
                current = {
                    "date": day_date.isoformat(), "weekday": match[2],
                    "title": match[3], "lines": [(page_num, match[3])],
                    "page": page_num, "context": context,
                }
            elif current:
                current["lines"].append((page_num, line))
    if current:
        blocks.append(current)
    expected = {(START + timedelta(days=i)).isoformat() for i in range((END-START).days+1)}
    actual = {b['date'] for b in blocks}
    if actual != expected:
        raise ValueError(f"Kalendarium unvollständig: fehlend={sorted(expected-actual)}, zusätzlich={sorted(actual-expected)}")
    if len(blocks) != len(expected) + 1:
        raise ValueError("Unerwartete Anzahl Kalenderabschnitte (25. Oktober hat zwei Varianten).")
    duplicates = {d: c for d, c in Counter(b['date'] for b in blocks).items() if c > 1}
    if duplicates != {"2027-10-25": 2}:
        raise ValueError(f"Unerwartete Datumsvarianten: {duplicates}")
    return blocks


def split_languages(text):
    """Nur explizite Übersetzungen abtrennen, keine Übersetzung erfinden."""
    text = clean(text).lstrip('+ ').strip()
    if ' / ' in text:
        de, sl = text.split(' / ', 1)
        return de.strip(), sl.lstrip('+ ').strip() or None
    # Im Directorium stehen Übersetzungen auch ohne Schrägstrich darunter.
    markers = (
        r"\+\s*\d+\.\s*(?:ADVENTNA|POSTNA|VELIKONOČNA|NAVADNA)",
        r"\+?\s*(?:\d+\.\s*(?:NEDELJA|DAN)|SV\.|SVETI\b|MARIJA,|NEDOLŽNI\b|JEZUSOVO\b|JEZUSOVA\b|JEZUS\b|GOSPODOVO\b|GOSPODOV\b|SPOMIN\b|OBLETNICA\b|SPREOBRNITEV\b|SEDEŽ\b|CVETNA\b|V ČAST\b|ROJSTVO\b|OBISKANJE\b|VNEBOVZETJE\b|POSVETITEV\b|TOREK\b|SREDA\b|ČETRTEK\b|PETEK\b|SOBOTA\b|BINKOŠTNI\b)",
    )
    found = []
    for pattern in markers:
        match = re.search(r"\s+(" + pattern + r")", text)
        if match:
            found.append(match.start())
    if found:
        pos = min(found)
        return text[:pos].strip(), text[pos:].strip().lstrip('+ ').strip()
    return text, None


def kind_for(name, rank):
    if rank == 'sunday':
        return 'sunday'
    if re.search(r"\b(?:Hl\.|Hll\.|HL\.|HLL\.|Sel\.|SEL\.)|heiligen Märtyrer|UNSCHULDIGE KINDER|Heilige Schutzengel", name):
        return 'saint'
    if re.search(r"Maria|Mariä|Marien|MARIÄ|MARIEN|GOTTESMUTTER|Unser[e]? Liebe Frau|Herz Mari", name, re.I):
        return 'marian'
    return 'feast'


def parse_block(block):
    # Die Überschriften stehen vor der ersten Offiziums-/Messanweisung.
    header = []
    for page, line in block['lines']:
        if re.search(r"\bOff\b", line) or re.match(r"^(?:[WRV]|GR|V/ROSA)\s+(?:M\b|DIE FEIER)", line):
            prefix = re.match(r"^([HFGg])\s+Off\b", line)
            if prefix:
                header.append((page, prefix[1]))
            break
        header.append((page, line))
    if not header:
        raise ValueError(f"Keine Überschrift: {block['date']}")
    records, notes = [], []
    primary_lines, primary_page = [], header[0][0]
    optional = None
    primary_rank = None
    off_index = next((i for i, (_, line) in enumerate(block['lines']) if re.search(r'\bOff\b', line)), None)
    off_text = join_lines([line for _, line in block['lines'][off_index:off_index+4]]) if off_index is not None else ''

    def add(text, rank, page, status, note=None):
        de, sl = split_languages(text)
        if not de:
            raise ValueError(f"Leere Feier am {block['date']}")
        scopes = re.findall(r"\b(?:RK|DK|ÖBK|GK)\b", text)
        records.append({
            'name': de, 'name_sl': sl, 'rank_code': rank,
            'kind': kind_for(de, rank), 'calendar_scope': ','.join(dict.fromkeys(scopes)) or 'unspecified',
            'observance_status': status, 'applicability_note': note,
            'source_page': page, 'source_text': text,
        })

    def flush_optional():
        nonlocal optional
        if optional:
            text = join_lines(optional['lines'])
            rank = optional['rank']
            status = 'optional' if rank == 'g' else 'observed'
            if 'Kommemoration' in off_text:
                status = 'commemoration_only'
            # Scholastika steht ausdrücklich bei Aschermittwoch ohne Erklärung.
            if block['date'] == '2027-02-10':
                status = 'suppressed'
            add(text, rank, optional['page'], status)
            optional = None

    # Unterdrückte Feiern können sich über zwei Zeilen erstrecken.
    suppressed_names = []
    consumed = set()
    for idx, (page, line) in enumerate(header):
        if re.search(r"entf(?:ällt|allen) in diesem Jahr", line):
            start = idx
            if idx > 0 and (line.startswith('KLAGENFURT ') or line.startswith('entf')):
                start = idx - 1
            text = join_lines([l for _, l in header[start:idx+1]])
            text = re.sub(r'^[HFGg]\s+', '', text)
            m = SUPPRESSED.fullmatch(text)
            if not m:
                raise ValueError(f"Entfallene Feier nicht erkannt: {text}")
            suppressed_names.append((page, m[1], text))
            consumed.update(range(start, idx+1))
            if start == idx:
                # Vorangestelltes H/G bezeichnet die Hauptfeier dieses Tages.
                rm = RANK.fullmatch(line)
                if rm and rm[1] in 'HFG':
                    primary_rank = rm[1]

    note_prefixes = ('Monatlicher ', 'Priestersamstag', 'Heute ', 'Fast- und ', 'Im Dom ', 'Weihe des Domes', 'in der Stadthauptpfarrkirche', 'Landespatron ', 'Diözesanpatron ', 'DIE DREI ÖSTERLICHEN', 'Zum Fasten-', '(keine Eucharistiefeier)')
    note_mode = False
    for idx, (page, line) in enumerate(header):
        if idx in consumed:
            continue
        rm = RANK.fullmatch(line)
        if rm:
            rank, rest = rm[1], rm[2] or ''
            if rank == 'g' or (rank in 'GF' and re.match(r'(?:Hl\.|Hll\.|Sel\.|Unsere Liebe)', rest)):
                flush_optional()
                optional = {'rank': rank, 'page': page, 'lines': [rest]}
                note_mode = False
                continue
            # Das F am umgebrochenen Titel des Dornenhauptfestes ist ein
            # eigener Rang in der Randspalte, kein zusätzlicher Eintrag.
            if rest.startswith('JESU CHRISTI'):
                primary_rank = rank
                primary_lines.append(rest)
                continue
            if rank == 'H' and rest.startswith('in der Stadthauptpfarrkirche'):
                notes.append(line)
                continue
            primary_rank = primary_rank or rank
            if rest:
                notes.append(rest)
                note_mode = True
            continue
        if 'Monatlicher Gebetstag' in line and not line.startswith('Monatlicher '):
            title_part, note_part = line.split('Monatlicher Gebetstag', 1)
            primary_lines.append(title_part.strip())
            notes.append('Monatlicher Gebetstag' + note_part)
            note_mode = True
            continue
        if line.startswith(note_prefixes):
            notes.append(line)
            note_mode = True
            continue
        if note_mode:
            notes.append(line)
            continue
        if optional:
            optional['lines'].append(line)
        else:
            primary_lines.append(line)
    flush_optional()

    title = join_lines(primary_lines)
    # Normale Wochentage werden in calendar_days/source_day_blocks geführt.
    is_weekday = bool(re.match(r'^(?:der |nach |DER KARWOCHE)', title))
    if block['date'] == '2027-03-15':
        title = re.sub(r'^der 5\. Fastenwoche\s+', '', title)
        is_weekday = False
    if not is_weekday:
        rank = primary_rank
        if rank is None:
            if 'DER OSTEROKTAV' in title or 'WEIHNACHTSOKTAV' in title or title.startswith('OSTERMONTAG'):
                rank = 'octave'
            elif block['date'] in ('2027-03-25','2027-03-26','2027-03-27'):
                rank = 'triduum'
            elif title.startswith('ASCHERMITTWOCH'):
                rank = 'privileged_weekday'
            elif title.startswith('ALLERSEELEN'):
                rank = 'commemoration'
            elif block['weekday'] == 'So':
                rank = 'sunday'
            else:
                raise ValueError(f"Rang fehlt: {block['date']} {title}")
        status, note = 'observed', None
        if block['date'] == '2027-10-25':
            status, note = 'conditional', 'Nur für Kirchen, die ihren Weihetag nicht kennen.'
        add(title, rank, primary_page, status, note)
        if block['date'] == '2027-03-28':
            records[-1]['name'] += ' – OSTERSONNTAG'
            records[-1]['name_sl'] = 'VELIKONOČNA NEDELJA'
    for page, name, raw in suppressed_names:
        # Wenn mehrere Namen ausdrücklich getrennt genannt sind, bleiben sie
        # gemeinsam wie in der Quelle; ein Fest kann mehrere Heilige umfassen.
        add(name, None, page, 'suppressed', raw)

    # Lokale Alternativen, deren Rang und Geltungsbereich im Text erläutert sind.
    if block['date'] == '2027-05-17':
        records = [r for r in records if r['name'] != 'Maria, Mutter der Kirche']
        # Pfingstmontag und der Mariengedenktag sind eigenständige Alternativen.
        for record in records:
            if record['name'].startswith('PFINGSTMONTAG'):
                record['name'] = 'PFINGSTMONTAG'
                record['name_sl'] = 'BINKOŠTNI PONEDELJEK'
                record['rank_code'] = 'privileged_weekday'
        add('Maria, Mutter der Kirche', 'G', primary_page, 'conditional',
            'Directorium: gewohnte liturgische Ordnung des Pfingstmontags bleibt bestehen; örtliche Auswahl beachten.')
    if block['date'] == '2027-09-19':
        records = [r for r in records if r['name'] != 'JAHRESTAG DER WEIHE DES DOMES ZU KLAGENFURT']
        add('JAHRESTAG DER WEIHE DES DOMES ZU KLAGENFURT', 'H', primary_page,
            'conditional', 'Nur im Dom zu Klagenfurt; außerhalb entfällt die Feier in diesem Jahr.')
    # Das Fest des Dornenhauptes ist in St. Egid örtlich ein Hochfest.
    if block['date'] == '2027-03-15':
        for r in records:
            if r['rank_code'] == 'F':
                r['applicability_note'] = 'In der Stadthauptpfarrkirche St. Egid in Klagenfurt im Rang H.'
                r['name_sl'] = 'PRAZNIK S TRNJEM KRONANE GLAVE'
    if block['date'] == '2027-03-25':
        for r in records:
            if r['rank_code'] == 'triduum':
                r['name'] = 'GRÜNDONNERSTAG oder HOHER DONNERSTAG'
                r['name_sl'] = 'VELIKI ČETRTEK'
    for r in records:
        r['review_notes'] = ''
        if r['name'].startswith('Hl. Scholastika'):
            r['review_notes'] = 'Am Aschermittwoch verdrängt; Quelle druckt G ohne ausdrücklichen Entfallvermerk. Fachlich prüfen.'
        if r['name_sl'] and 'muoeenica' in r['name_sl']:
            r['review_notes'] = 'Auffällige Zeichenkodierung im slowenischen PDF-Text (muoeenica); vor Ausgabe sprachlich prüfen.'
    return records, '\n'.join(notes)


def import_pdf(conn, source=SOURCE):
    migrate(conn)
    source = Path(source)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError('Diese Datei ist nicht die unterstützte Directorium-Ausgabe. Für neue/geänderte Quellen muss der Importer geprüft werden.')
    existing = conn.execute('SELECT id, report_json FROM import_runs WHERE source_sha256=?', (digest,)).fetchone()
    if existing:
        return {'already_imported': True, 'import_run_id': existing['id'], **json.loads(existing['report_json'])}
    if conn.execute('SELECT 1 FROM import_runs WHERE liturgical_year=?', (YEAR,)).fetchone():
        raise ValueError('Für 2026/27 existiert bereits eine andere Quelle. Kein automatisches Überschreiben.')
    reader = PdfReader(source)
    if len(reader.pages) != 227:
        raise ValueError('Dieser Importer unterstützt nur das vorhandene 227-seitige Directorium 2026/27.')
    pages = [p.extract_text() for p in reader.pages]
    if '2026/2027' not in pages[0] or 'Gurk' not in pages[0]:
        raise ValueError('Unerwartete Directorium-Ausgabe.')
    blocks = extract_blocks(pages)
    parsed = [(b, *parse_block(b)) for b in blocks]
    counts = Counter(r['observance_status'] for _, records, _ in parsed for r in records)
    report = {
        'source_pages': len(pages), 'calendar_days': len({b['date'] for b in blocks}),
        'calendar_blocks': len(blocks), 'celebrations': sum(counts.values()),
        'by_status': dict(counts), 'start': START.isoformat(), 'end': END.isoformat(),
        'review_status': 'needs_review',
        'warnings': [
            'Automatisch extrahiert und technisch geprüft; fachliche Freigabe steht aus.',
            'Die Quelle enthält widersprüchliche Übersichten (Lesejahr A/B; Fronleichnam und Herz-Jesu-Termine). Importiert wurden die datierten Tagesabschnitte.',
            'Rangcodes ersetzen keine vollständige Vorrangberechnung. Örtliche Sonderfälle sind bedingt verfügbar.',
            'Fehlende slowenische Texte sind NULL; keine automatisch erfundenen Übersetzungen.',
        ],
    }
    with conn:
        cursor = conn.execute(
            'INSERT INTO import_runs(source_file,source_sha256,liturgical_year,parser_version,status,report_json) VALUES(?,?,?,?,?,?)',
            (source.name, digest, YEAR, PARSER_VERSION, 'imported_needs_review', json.dumps(report, ensure_ascii=False)),
        )
        run_id = cursor.lastrowid
        for num, text in enumerate(pages, 1):
            first = text.splitlines()[0].strip() if text.splitlines() else ''
            conn.execute('INSERT INTO source_pages VALUES(?,?,?,?)', (run_id, num, first if first.isdigit() else None, text))
        day_ids, variants = {}, Counter()
        for block, records, notes in parsed:
            day = block['date']
            if day not in day_ids:
                c = conn.execute('INSERT INTO calendar_days(import_run_id,liturgical_year,calendar_date,weekday) VALUES(?,?,?,?)',
                                 (run_id, YEAR, day, block['weekday']))
                day_ids[day] = c.lastrowid
            variants[day] += 1
            c = conn.execute('INSERT INTO source_day_blocks(calendar_day_id,variant,header_text,header_notes,source_page_start,source_page_end,raw_text) VALUES(?,?,?,?,?,?,?)',
                             (day_ids[day], variants[day], block['title'], notes, block['page'], block['lines'][-1][0], '\n'.join(l for _, l in block['lines'])))
            block_id = c.lastrowid
            for ordinal, record in enumerate(records, 1):
                row = {
                    'calendar_day_id': day_ids[day], 'source_block_id': block_id,
                    'source_key': f'{digest}:{day}:{variants[day]}:{ordinal}',
                    'liturgical_year': YEAR, 'celebration_date': day, **record,
                    'source_reference': f'{source.name}, PDF-Seite {record["source_page"]} (Druckseite {record["source_page"]-2})',
                }
                columns = ','.join(row)
                conn.execute(f'INSERT INTO saints({columns}) VALUES({",".join("?" for _ in row)})', tuple(row.values()))
        if conn.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Ungültige Fremdschlüssel im Import.')
    return {'already_imported': False, 'import_run_id': run_id, **report}
