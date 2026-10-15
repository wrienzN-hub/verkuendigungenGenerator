import hashlib
import json
from datetime import date, timedelta

from ..core.config import ROOT
from ..repositories.saints import list_celebrations
from ..schemas.documents import DocumentPayload
from .document_rendering import template_supported
from .liturgical_weeks import list_weeks


def template_source(conn, template_id):
    if template_id == 0:
        return {'id': 0, 'parish_name': 'Eberndorf', 'name': 'Eberndorf – vorhandene Vorlage', 'source_filename': 'vorlage.docx', 'docx': (ROOT / 'resources/vorlage.docx').read_bytes()}
    row = conn.execute('SELECT * FROM document_templates WHERE id=?', (template_id,)).fetchone()
    if row is None:
        raise LookupError('Vorlage nicht gefunden.')
    return dict(row)


def options(conn):
    templates = [template_source(conn, 0)] + [dict(row) for row in conn.execute('SELECT id,parish_name,name,source_filename,docx FROM document_templates ORDER BY parish_name,name')]
    result = []
    for item in templates:
        data = item.pop('docx')
        item['supported'] = template_supported(data)
        result.append(item)
    # Generator years use the actual imported liturgical years, not the
    # December-to-November browsing window of the saints administration.
    years = [row[0] for row in conn.execute('SELECT DISTINCT liturgical_year FROM import_runs ORDER BY liturgical_year DESC')]
    return {'templates': result, 'years': years}


def generation_weeks(conn, year):
    row = conn.execute('SELECT min(calendar_date),max(calendar_date) FROM calendar_days WHERE liturgical_year=?', (year,)).fetchone()
    if not row or row[0] is None:
        return []
    # Include the opening Advent Sunday in November and exclude the next year.
    candidates = list_weeks(conn, year)
    first = int(year[:4])
    candidates += list_weeks(conn, f'{first-1}/{first % 100:02d}')
    unique = {week['id']: week for week in candidates if row[0] <= week['start'] < row[1]}
    return sorted(unique.values(), key=lambda week: (week['start'], week['season']))


def prepare(conn, template_id, year, week_id):
    template = template_source(conn, template_id)
    if not template_supported(template['docx']):
        raise ValueError('Diese Word-Vorlage benötigt einen eigenen Absatz mit {{inhalt}} oder die unterstützte Wochentabelle.')
    week = next((item for item in generation_weeks(conn, year) if item['id'] == week_id), None)
    if week is None:
        raise ValueError('Die gewählte Woche ist im Directorium dieses Kirchenjahres nicht vorhanden.')
    start, end = date.fromisoformat(week['start']), date.fromisoformat(week['end'])
    missing = []
    days = []
    celebrations = list_celebrations(conn, start.isoformat(), end.isoformat(), available_only=True)
    for index in range(8):
        day = (start + timedelta(days=index)).isoformat()
        if conn.execute('SELECT 1 FROM calendar_days WHERE calendar_date=?', (day,)).fetchone() is None:
            missing.append(day)
        entries = [item for item in celebrations if item['celebration_date'] == day]
        # Source-year overlaps must not print the same feast twice.
        unique = {}
        for item in entries:
            unique.setdefault((item['name'], item['name_sl']), item)
        days.append({'id': 'day-' + day, 'date': day, 'enabled': True,
            'celebrations': [{'id': 'celebration-' + str(item['id']), 'source_celebration_id': item['id'], 'title': {'de': item['name'], 'sl': item['name_sl'] or ''}, 'rank': item['rank_code'], 'enabled': item['observance_status'] == 'observed'} for item in unique.values()],
            'services': [], 'notices': []})
    payload = DocumentPayload.model_validate({'schema_version': 1, 'template_id': template_id, 'template_version': hashlib.sha256(template['docx']).hexdigest(),
        'parish': {'id': template['parish_name'], 'name': {'de': template['parish_name'], 'sl': ''}},
        'selection': {'liturgical_year': year, 'season': week['season'], 'week': week['week'], 'week_id': week_id},
        'period': {'start': start, 'end': end}, 'days': days})
    warnings = ['Für folgende Tage fehlen Kalenderdaten: ' + ', '.join(missing) + '. Bitte die Einträge ergänzen.'] if missing else []
    return {'payload': payload.model_dump(mode='json', by_alias=True), 'warnings': warnings}


def validate_selection(conn, payload):
    week = next((item for item in generation_weeks(conn, payload.selection.liturgical_year) if item['id'] == payload.selection.week_id), None)
    if week is None or week['start'] != payload.period.start.isoformat() or week['end'] != payload.period.end.isoformat() or week['season'] != payload.selection.season or week['week'] != payload.selection.week:
        raise ValueError('Die Auswahl passt nicht zum Zeitraum im liturgischen Kalender.')


def read_document(conn, document_id):
    row = conn.execute('SELECT id,payload_json,revision,created_at,updated_at,generated_pdf IS NOT NULL AS has_pdf FROM document_payloads WHERE id=?', (document_id,)).fetchone()
    if row is None:
        raise LookupError('Abkündigung nicht gefunden.')
    result = dict(row)
    result['payload'] = json.loads(result.pop('payload_json'))
    result['has_pdf'] = bool(result['has_pdf'])
    return result
