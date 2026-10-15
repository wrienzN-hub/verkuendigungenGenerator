"""Directorien der Diözese Gurk mit datierten Monatsabschnitten importieren."""

import hashlib
import json
import re
import unicodedata
from io import BytesIO
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from pypdf import PdfReader

from ..core.config import ROOT
from ..infrastructure.database import migrate

SOURCE = ROOT / "resources/directorium-2026-27-kern_21092026.pdf"
PARSER_VERSION = "gurk-monthly-v4"
SOURCE_SHA256 = 'e44ce1c4b155a77ca6f36b1ae0c5d8f4495c4e3207a63ce0ab84d1a12b761f4a'
YEAR = "2026/27"
START, END = date(2026, 11, 29), date(2027, 11, 27)
MONTHS = {
    "NOVEMBER": 11, "DEZEMBER": 12, "JÄNNER": 1, "FEBER": 2,
    "MÄRZ": 3, "APRIL": 4, "MAI": 5, "JUNI": 6, "JULI": 7,
    "JANUAR": 1, "FEBRUAR": 2,
    "AUGUST": 8, "SEPTEMBER": 9, "OKTOBER": 10,
}
DAY = re.compile(r"^(\d{1,2})\s+(Mo|Di|Mi|Do|Fr|Sa|So)\s+(.+)$")
MONTH = re.compile(r"^(" + "|".join(MONTHS) + r")\s+(20\d{2})$", re.I)
RANK = re.compile(r"^([HFGg])(?:\s+(.*))?$")
SUPPRESSED = re.compile(r"(.+?)\s+entf(?:ällt|allen)\s+in diesem Jahr\.", re.I)
WEEKDAYS = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']


def clean(value):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value)).strip()


def join_lines(lines):
    # Ein echter Bindestrich am Zeilenende wird bei Worttrennung aufgelöst.
    return clean(re.sub(r"-\n(?=[a-zäöüßčšž])", "", "\n".join(lines)))


class ImportConflict(ValueError):
    """Eine andere Ausgabe für dieses Kirchenjahr ist bereits vorhanden."""


def first_advent(year):
    earliest = date(year, 11, 27)
    return earliest + timedelta(days=(6 - earliest.weekday()) % 7)


def detect_year(pages):
    front = '\n'.join(pages[:6])
    if not re.search(r'Gurk|Krška', front, re.I):
        raise ValueError('Das PDF ist kein erkennbares Directorium der Diözese Gurk.')
    years = set()
    for match in re.finditer(r'\b(20\d{2})\s*/\s*(20\d{2}|\d{2})\b', front):
        first = int(match[1])
        second = int(match[2]) if len(match[2]) == 4 else 2000 + int(match[2])
        if second == first + 1:
            years.add(first)
    if len(years) != 1:
        raise ValueError('Das Kirchenjahr konnte auf den ersten PDF-Seiten nicht eindeutig erkannt werden.')
    first = years.pop()
    return f'{first}/{str(first+1)[-2:]}', first_advent(first), first_advent(first+1)-timedelta(days=1)


def extract_blocks(pages, start=START, end=END):
    blocks, current = [], None
    month = year = None
    for page_num, text in enumerate(pages, 1):
        month_matches = [MONTH.fullmatch(line.strip()) for line in text.splitlines()]
        month_match = next((m for m in month_matches if m), None)
        if month_match:
            month, year = MONTHS[month_match[1].upper()], int(month_match[2])
        if month is None:
            continue
        lines = text.splitlines()
        for index, raw_line in enumerate(lines):
            line = clean(raw_line)
            if not line or line.isdigit() or MONTH.fullmatch(line):
                continue
            match = DAY.fullmatch(line)
            if match:
                day_date = date(year, month, int(match[1]))
                if not start <= day_date <= end:
                    continue
                if WEEKDAYS[day_date.weekday()] != match[2]:
                    raise ValueError(f"Wochentag stimmt nicht: {day_date} ({match[2]})")
                if current:
                    if day_date.isoformat() < current['date']:
                        raise ValueError(f'Kalenderabschnitte sind nicht chronologisch: {day_date}.')
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
    expected = {(start + timedelta(days=i)).isoformat() for i in range((end-start).days+1)}
    actual = {b['date'] for b in blocks}
    # Einzelne Lücken in der Quelle sind zulässig. Eine weitgehend nicht
    # erkannte Ausgabe bleibt ein Layoutfehler, statt als Import zu gelten.
    if len(actual) < len(expected) * 0.9:
        raise ValueError('Weniger als 90 % der Kalendertage erkannt. Das PDF ist unvollständig oder sein Layout wird nicht unterstützt.')
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


def celebration_name(text):
    """Berufs-/Standesangaben entfernen; gemeinsame Namen erhalten."""
    if text is None:
        return None
    if text == 'Maria, Mutter der Kirche':
        return text  # Eigenständiger Name des Mariengedenktags.
    text = re.sub(r'\s*\((?:RK|DK|GK|ÖBK|Verlegung|vgl\b)[^)]*\)', '', text)
    roles = re.compile(
        r'^(?:Priester|Ordenspriester|Ordensmann|Ordensfrau|Ordensbruder|Ordensgründer|'
        r'Kirchenlehrer|Kirchenlehrerin|Bisch(?:of|öfe)|Abtbischof|Abt|Äbtissin|Papst|Diakon|'
        r'Märtyrer|Märtyrin|Jungfrau|Glaubensbote|Glaubensboten|Einsiedler|Mönch|'
        r'Mystiker|Mystikerin|König|Kaiser|Herzog|Landgr[aä]f|Markgraf|Reichskanzler|Lordkanzler|'
        r'Philosoph|Familienvater|Ehefrau|Mutter|Stifterin|Schutzpatron|Patronin|'
        r'Eltern|Bräutigam|Apostel|Apostolin|Evangelist|Erzengel|Friedensstifter|Seelsorger|'
        r'Witwe|Volksprediger|Wanderprediger|Gründer|Pfarrer|'
        r'Pries\s+ter|erster Märtyrer|erste[rn]? Märtyrer|'
        r'apostol|redovnic|redovnik|devica|cerkvena učiteljica|sozavetnica|'
        r'menih|škof|zavetnik|zavetnica|diakon|mučen|muoeenica|ustanovitelj|'
        r'prvi mučenec|ženin|mati\b|nadangeli)', re.I,
    )
    parts = []
    for part in text.split(','):
        part = part.strip()
        if not part:
            continue
        if parts and roles.match(part):
            # Manche Namen stehen im selben Abschnitt hinter einer Funktion.
            following = re.search(r'\b(?:und\s+(?:h[lL][lL]?\.?\s+)|und\s+hll\.\s+).+', part)
            if following:
                parts.append(following[0])
            continue
        parts.append(part)
    result = ''
    for part in parts:
        result += ((' ' if re.match(r'^(?:und|in)\b', part) else ', ') if result else '') + part
    return clean(result)


def refresh_import_names(conn, run_id):
    """Bestehenden Import ohne neue IDs oder Verlust manueller Schalter anpassen."""
    rows = conn.execute(
        'SELECT s.id,s.name,s.name_sl FROM saints s JOIN calendar_days d ON d.id=s.calendar_day_id WHERE d.import_run_id=?',
        (run_id,),
    ).fetchall()
    changed = 0
    with conn:
        for row in rows:
            name, name_sl = celebration_name(row['name']), celebration_name(row['name_sl'])
            if (name, name_sl) != (row['name'], row['name_sl']):
                conn.execute("UPDATE saints SET name=?,name_sl=?,updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?", (name, name_sl, row['id']))
                changed += 1
        conn.execute('UPDATE import_runs SET parser_version=? WHERE id=?', (PARSER_VERSION, run_id))
    return changed


def parse_block(block, *, known_edition=True):
    # Die Überschriften stehen vor der ersten Offiziums-/Messanweisung.
    header = []
    for page, line in block['lines']:
        if re.search(r"\bOff\b", line) or re.match(r"^(?:[WRV]|GR|V/ROSA)\s+(?:M\b|DIE FEIER)", line):
            prefix = re.match(r"^([HFGg])\s+Off\b", line)
            if prefix and prefix[1] != 'g':
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
            if known_edition and block['date'] == '2027-02-10':
                status = 'suppressed'
            add(text, rank, optional['page'], status)
            optional = None

    # Unterdrückte Feiern können sich über zwei Zeilen erstrecken.
    suppressed_names = []
    consumed = set()
    for idx, (page, line) in enumerate(header):
        if re.search(r"entf(?:ällt|allen) in diesem Jahr", line):
            start = idx
            if idx > 0 and (line.startswith('KLAGENFURT ') or line.startswith('entf') or header[idx-1][1].endswith(('Hl.','HL.','Hll.','HLL.'))):
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
    if 'FEST DES DORNENGEKRÖNTEN' in title:
        title = re.sub(r'^der \d+\. Fastenwoche\s+', '', title)
        is_weekday = False
    if not is_weekday:
        rank = primary_rank
        if rank is None:
            if 'DER OSTEROKTAV' in title or 'WEIHNACHTSOKTAV' in title or title.startswith('OSTERMONTAG'):
                rank = 'octave'
            elif title.startswith(('GRÜNDONNERSTAG','KARFREITAG','KARSAMSTAG')):
                rank = 'triduum'
            elif title.startswith('ASCHERMITTWOCH'):
                rank = 'privileged_weekday'
            elif title.startswith('PFINGSTMONTAG'):
                rank = 'privileged_weekday'
            elif title.startswith('ALLERSEELEN'):
                rank = 'commemoration'
            elif block['weekday'] == 'So':
                rank = 'sunday'
            else:
                raise ValueError(f"Rang fehlt: {block['date']} {title}")
        status, note = 'observed', None
        if 'JAHRESTAG DER KIRCHWEIHE' in title and 'ihren Weihetag nicht kennen' in block['context']:
            status, note = 'conditional', 'Nur für Kirchen, die ihren Weihetag nicht kennen.'
        add(title, rank, primary_page, status, note)
        if 'HOCHFEST DER AUFERSTEHUNG DES HERRN' in title and 'OSTERSONNTAG' in title:
            records[-1]['name'] += ' – OSTERSONNTAG'
            records[-1]['name_sl'] = 'VELIKONOČNA NEDELJA'
    for page, name, raw in suppressed_names:
        # Wenn mehrere Namen ausdrücklich getrennt genannt sind, bleiben sie
        # gemeinsam wie in der Quelle; ein Fest kann mehrere Heilige umfassen.
        add(name, None, page, 'suppressed', raw)

    # Lokale Alternativen, deren Rang und Geltungsbereich im Text erläutert sind.
    if block['title'] == 'PFINGSTMONTAG' and any('Maria, Mutter der Kirche' in line for _,line in header):
        records = [r for r in records if r['name'] != 'Maria, Mutter der Kirche']
        # Pfingstmontag und der Mariengedenktag sind eigenständige Alternativen.
        for record in records:
            if record['name'].startswith('PFINGSTMONTAG'):
                record['name'] = 'PFINGSTMONTAG'
                record['name_sl'] = 'BINKOŠTNI PONEDELJEK'
                record['rank_code'] = 'privileged_weekday'
        add('Maria, Mutter der Kirche', 'G', primary_page, 'conditional',
            'Directorium: gewohnte liturgische Ordnung des Pfingstmontags bleibt bestehen; örtliche Auswahl beachten.')
    if any(line.startswith('Im Dom zu Klagenfurt: H') for _,line in header):
        records = [r for r in records if r['name'] != 'JAHRESTAG DER WEIHE DES DOMES ZU KLAGENFURT']
        add('JAHRESTAG DER WEIHE DES DOMES ZU KLAGENFURT', 'H', primary_page,
            'conditional', 'Nur im Dom zu Klagenfurt; außerhalb entfällt die Feier in diesem Jahr.')
    # Das Fest des Dornenhauptes ist in St. Egid örtlich ein Hochfest.
    if 'FEST DES DORNENGEKRÖNTEN' in title:
        for r in records:
            if r['rank_code'] == 'F':
                r['applicability_note'] = 'In der Stadthauptpfarrkirche St. Egid in Klagenfurt im Rang H.'
                r['name_sl'] = 'PRAZNIK S TRNJEM KRONANE GLAVE'
    if title.startswith('GRÜNDONNERSTAG'):
        for r in records:
            if r['rank_code'] == 'triduum':
                r['name'] = 'GRÜNDONNERSTAG oder HOHER DONNERSTAG'
                r['name_sl'] = 'VELIKI ČETRTEK'
    for r in records:
        r['name'] = celebration_name(r['name'])
        r['name_sl'] = celebration_name(r['name_sl'])
    return records, '\n'.join(notes)


def import_pdf(conn, source=SOURCE, *, pdf_bytes=None, filename=None):
    migrate(conn)
    data = Path(source).read_bytes() if pdf_bytes is None else pdf_bytes
    source_name = (filename or Path(source).name).replace('\\','/').split('/')[-1]
    digest = hashlib.sha256(data).hexdigest()
    existing = conn.execute('SELECT id, liturgical_year, parser_version, report_json FROM import_runs WHERE source_sha256=?', (digest,)).fetchone()
    if existing:
        changed = refresh_import_names(conn, existing['id']) if existing['parser_version'] == 'gurk-2026-27-v1' else 0
        with conn:
            conn.execute('UPDATE import_runs SET source_pdf=coalesce(source_pdf,?) WHERE id=?', (data,existing['id']))
        return {'already_imported': True, 'import_run_id': existing['id'], 'updated_names': changed, **json.loads(existing['report_json']), 'liturgical_year': existing['liturgical_year']}
    if not data.startswith(b'%PDF-'):
        raise ValueError('Die Datei ist kein gültiges PDF.')
    try:
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted:
            raise ValueError('Passwortgeschützte PDFs werden nicht unterstützt.')
        if not 1 <= len(reader.pages) <= 1000:
            raise ValueError('Das PDF muss zwischen 1 und 1000 Seiten enthalten.')
        pages = [p.extract_text() or '' for p in reader.pages]
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError('Das PDF kann nicht gelesen werden. Bitte eine unbeschädigte Datei mit auswählbarem Text hochladen.') from exc
    year, start, end = detect_year(pages)
    if conn.execute('SELECT 1 FROM import_runs WHERE liturgical_year=?', (year,)).fetchone():
        raise ImportConflict(f'Für {year} ist bereits ein anderes Directorium importiert. Bestehende Daten werden nicht überschrieben.')
    blocks = extract_blocks(pages, start, end)
    parsed = [(b, *parse_block(b, known_edition=digest==SOURCE_SHA256)) for b in blocks]
    if not any(records for _,records,_ in parsed):
        raise ValueError('Keine liturgischen Feiern erkannt. Dieses PDF-Layout wird nicht unterstützt.')
    counts = Counter(r['observance_status'] for _, records, _ in parsed for r in records)
    present_dates = {b['date'] for b in blocks}
    expected_dates = {(start+timedelta(days=i)).isoformat() for i in range((end-start).days+1)}
    missing_dates = sorted(expected_dates-present_dates)
    gap_warnings = []
    if missing_dates:
        shown = ', '.join(date.fromisoformat(d).strftime('%d.%m.%Y') for d in missing_dates[:5])
        gap_warnings.append(f'Für {len(missing_dates)} Kalendertag(e) wurde kein Quellenabschnitt gefunden: {shown}'
                            + (' …' if len(missing_dates)>5 else '')
                            + '. Die vorhandenen Einträge wurden importiert; für die fehlenden Tage wurden keine Feiern ergänzt.')
    report = {
        'source_pages': len(pages), 'calendar_days': len({b['date'] for b in blocks}),
        'expected_calendar_days': len(expected_dates), 'missing_dates': missing_dates,
        'calendar_blocks': len(blocks), 'celebrations': sum(counts.values()),
        'liturgical_year': year,
        'by_status': dict(counts), 'start': start.isoformat(), 'end': end.isoformat(),
        'warnings': gap_warnings + ([
            'Die Quelle enthält widersprüchliche Übersichten (Lesejahr A/B; Fronleichnam und Herz-Jesu-Termine). Importiert wurden die datierten Tagesabschnitte.',
        ] if digest == SOURCE_SHA256 else []) + [
            'Rangcodes ersetzen keine vollständige Vorrangberechnung. Örtliche Sonderfälle sind bedingt verfügbar.',
            'Fehlende slowenische Texte sind NULL; keine automatisch erfundenen Übersetzungen.',
        ],
    }
    with conn:
        cursor = conn.execute(
            'INSERT INTO import_runs(source_file,source_sha256,liturgical_year,parser_version,report_json,source_pdf) VALUES(?,?,?,?,?,?)',
            (source_name, digest, year, PARSER_VERSION, json.dumps(report, ensure_ascii=False), data),
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
                                 (run_id, year, day, block['weekday']))
                day_ids[day] = c.lastrowid
            variants[day] += 1
            c = conn.execute('INSERT INTO source_day_blocks(calendar_day_id,variant,header_text,header_notes,source_page_start,source_page_end,raw_text) VALUES(?,?,?,?,?,?,?)',
                             (day_ids[day], variants[day], block['title'], notes, block['page'], block['lines'][-1][0], '\n'.join(l for _, l in block['lines'])))
            block_id = c.lastrowid
            for ordinal, record in enumerate(records, 1):
                row = {
                    'calendar_day_id': day_ids[day], 'source_block_id': block_id,
                    'source_key': f'{digest}:{day}:{variants[day]}:{ordinal}',
                    'liturgical_year': year, 'celebration_date': day, **record,
                    'source_reference': f'{source_name}, PDF-Seite {record["source_page"]}',
                }
                columns = ','.join(row)
                conn.execute(f'INSERT INTO saints({columns}) VALUES({",".join("?" for _ in row)})', tuple(row.values()))
        if conn.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Ungültige Fremdschlüssel im Import.')
    return {'already_imported': False, 'import_run_id': run_id, **report}
