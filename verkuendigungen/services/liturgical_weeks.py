"""Wochenauswahl aus den datierten Überschriften des importierten Directoriums."""

import re
from datetime import date, timedelta

SEASONS = {
    'advent': 'Advent',
    'christmas': 'Weihnachtszeit',
    'lent': 'Fastenzeit',
    'holy_week': 'Karwoche',
    'easter': 'Osterzeit',
    'ordinary_time': 'Im Jahreskreis',
}
PATTERNS = [
    ('advent', r'(\d+)\.\s*(?:ADVENTSONNTAG|Adventwoche)'),
    ('lent', r'(\d+)\.\s*(?:FASTENSONNTAG|Fastenwoche)'),
    ('easter', r'(\d+)\.\s*(?:SONNTAG DER OSTERZEIT|Osterwoche)'),
    ('ordinary_time', r'(\d+)\.\s*(?:SONNTAG|Woche) IM JAHRESKREIS'),
]


def year_bounds(year):
    match = re.fullmatch(r'(20\d{2})/(\d{2}|20\d{2}|2100)',year)
    if not match:
        raise ValueError('Das Jahr muss im Format 2026/27 angegeben werden.')
    first = int(match[1])
    second = int(match[2])
    if second != (first+1 if len(match[2])==4 else (first+1)%100):
        raise ValueError('Das Jahr muss zwei aufeinanderfolgende Jahre enthalten.')
    return date(first,12,1),date(first+1,11,30)


def list_weeks(conn, year):
    start,end=year_bounds(year)
    rows = conn.execute(
        'SELECT d.calendar_date,b.header_text FROM calendar_days d '
        'JOIN source_day_blocks b ON b.calendar_day_id=d.id '
        'WHERE d.calendar_date BETWEEN ? AND ? ORDER BY d.calendar_date,b.variant', (start.isoformat(),end.isoformat()),
    )
    weeks = {}
    for row in rows:
        day = date.fromisoformat(row['calendar_date'])
        text = row['header_text']
        season, number = None, None
        for candidate, pattern in PATTERNS:
            match = re.search(pattern, text, re.I)
            if match:
                season, number = candidate, int(match[1])
                break
        if season is None:
            if re.search(r'PALMSONNTAG|DER KARWOCHE|GRÜNDONNERSTAG|KARFREITAG|KARSAMSTAG', text, re.I):
                season = 'holy_week'
            elif re.search(r'OSTEROKTAV|OSTERMONTAG|AUFERSTEHUNG DES HERRN|OSTERSONNTAG', text, re.I):
                season, number = 'easter', 1
            elif re.search(r'ASCHERMITTWOCH|nach Aschermittwoch', text, re.I):
                season = 'lent'
            elif re.search(r'WEIHNACHTSOKTAV|WEIHNACHTSZEIT|NACH WEIHNACHTEN|GEBURT DES HERRN|HEILIGEN FAMILIE', text, re.I):
                season = 'christmas'
        if season is None:
            continue
        start = day - timedelta(days=(day.weekday()+1) % 7)
        end = start + timedelta(days=7)
        key = f'{season}:{start.isoformat()}'
        # Eine Wochentagsüberschrift benennt dieselbe Woche wie ihr Sonntag.
        label = f'{number}. Woche' if number is not None else SEASONS[season]
        if season == 'lent' and number is None:
            label = 'Beginn der Fastenzeit'
        weeks[key] = {
            'id': key, 'season': season, 'season_label': SEASONS[season],
            'week': number, 'label': label,
            'start': start.isoformat(), 'end': end.isoformat(),
        }
    return sorted(weeks.values(), key=lambda w: (w['start'], w['season']))
