"""Lesen und Aktivieren der liturgischen Feiern."""

from datetime import date


def get_saint(conn, saint_id):
    row = conn.execute('SELECT * FROM saints WHERE id=?', (saint_id,)).fetchone()
    return dict(row) if row else None


def list_celebrations(conn, start, end, *, available_only=True, year=None, search=None, disabled=None, limit=None, offset=0):
    if date.fromisoformat(start) > date.fromisoformat(end):
        raise ValueError('Das Ende liegt vor dem Beginn.')
    table = 'available_celebrations' if available_only else 'saints'
    clauses, params = ['celebration_date BETWEEN ? AND ?'], [start, end]
    if year is not None:
        clauses.append('liturgical_year=?')
        params.append(year)
    if search:
        clauses.append('(instr(lower(name),lower(?))>0 OR instr(lower(coalesce(name_sl,\'\')),lower(?))>0)')
        params.extend([search, search])
    if disabled is not None:
        clauses.append('disabled=?')
        params.append(int(disabled))
    sql = f'SELECT * FROM {table} WHERE ' + ' AND '.join(clauses) + ' ORDER BY celebration_date,id'
    if limit is not None:
        sql += ' LIMIT ? OFFSET ?'
        params.extend([limit, offset])
    return [dict(row) for row in conn.execute(sql, params)]


def set_disabled(conn, saint_id, disabled):
    with conn:
        cursor = conn.execute(
            "UPDATE saints SET disabled=?, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?",
            (int(disabled), saint_id),
        )
        if cursor.rowcount != 1:
            raise ValueError(f'Eintrag {saint_id} existiert nicht.')
