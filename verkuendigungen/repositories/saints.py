"""Lesen und Aktivieren der liturgischen Feiern."""

from datetime import date


def get_saint(conn, saint_id):
    row = conn.execute('SELECT * FROM saints WHERE id=?', (saint_id,)).fetchone()
    return dict(row) if row else None


def filter_query(start, end, *, available_only=True, year=None, search=None, disabled=None, month=None, rank=None, observance_status=None):
    if date.fromisoformat(start) > date.fromisoformat(end):
        raise ValueError('Das Ende liegt vor dem Beginn.')
    table = 'available_celebrations' if available_only else 'saints'
    clauses, params = ['celebration_date BETWEEN ? AND ?'], [start, end]
    if year is not None:
        clauses.append('liturgical_year=?')
        params.append(year)
    if search:
        clauses.append('(instr(casefold(name),casefold(?))>0 OR instr(casefold(name_sl),casefold(?))>0)')
        params.extend([search, search])
    if disabled is not None:
        clauses.append('disabled=?')
        params.append(int(disabled))
    if month is not None:
        clauses.append("substr(celebration_date,6,2)=?")
        params.append(f'{month:02d}')
    for column, value in [('rank_code',rank),('observance_status',observance_status)]:
        if value is not None:
            clauses.append(f'{column}=?')
            params.append(value)
    return f'FROM {table} WHERE ' + ' AND '.join(clauses), params


def list_celebrations(conn, start, end, *, limit=None, offset=0, **filters):
    query, params = filter_query(start,end,**filters)
    sql = 'SELECT * ' + query + ' ORDER BY celebration_date,id'
    if limit is not None:
        sql += ' LIMIT ? OFFSET ?'
        params.extend([limit, offset])
    return [dict(row) for row in conn.execute(sql, params)]


def count_celebrations(conn,start,end,**filters):
    query,params=filter_query(start,end,**filters)
    return conn.execute('SELECT count(*) '+query,params).fetchone()[0]


def update_saint(conn,saint_id,changes):
    allowed={'name','name_sl','rank_code','observance_status','disabled','applicability_note'}
    if not changes or not set(changes)<=allowed:
        raise ValueError('Ungültige Änderungen.')
    with conn:
        assignments=','.join(f'{column}=?' for column in changes)
        cursor=conn.execute(f"UPDATE saints SET {assignments},updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?",[*changes.values(),saint_id])
        if cursor.rowcount!=1:
            raise ValueError(f'Eintrag {saint_id} existiert nicht.')


def set_disabled(conn, saint_id, disabled):
    with conn:
        cursor = conn.execute(
            "UPDATE saints SET disabled=?, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?",
            (int(disabled), saint_id),
        )
        if cursor.rowcount != 1:
            raise ValueError(f'Eintrag {saint_id} existiert nicht.')
