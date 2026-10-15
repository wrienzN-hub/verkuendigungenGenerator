"""Kleine Verwaltung bis zur späteren Web-Oberfläche."""

import argparse
import csv
import json
from pathlib import Path

from .core.config import DEFAULT_DATABASE
from .infrastructure.database import database, migrate
from .repositories.saints import list_celebrations, set_disabled
from .services.directorium import SOURCE, import_pdf


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, default=DEFAULT_DATABASE)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('init')
    imp = commands.add_parser('import-directorium')
    imp.add_argument('--source', type=Path, default=SOURCE)
    listing = commands.add_parser('list')
    listing.add_argument('--start', required=True)
    listing.add_argument('--end', required=True)
    listing.add_argument('--all', action='store_true', help='Auch deaktivierte, entfallene und bedingte Feiern')
    for name in ('enable', 'disable'):
        toggle = commands.add_parser(name)
        toggle.add_argument('id', type=int)
    export = commands.add_parser('export')
    export.add_argument('output', type=Path)
    commands.add_parser('status')
    args = parser.parse_args()
    with database(args.db) as conn:
        migrate(conn)
        if args.command == 'init':
            print(f'Datenbank bereit: {args.db}')
        elif args.command == 'import-directorium':
            print(json.dumps(import_pdf(conn, args.source), ensure_ascii=False, indent=2))
        elif args.command == 'list':
            print(json.dumps(list_celebrations(conn, args.start, args.end, available_only=not args.all), ensure_ascii=False, indent=2))
        elif args.command in ('enable', 'disable'):
            set_disabled(conn, args.id, args.command == 'disable')
            print(f'Eintrag {args.id}: {args.command}')
        elif args.command == 'export':
            rows = [dict(r) for r in conn.execute('SELECT * FROM saints ORDER BY celebration_date,id')]
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open('w', encoding='utf-8-sig', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=[c[1] for c in conn.execute('PRAGMA table_info(saints)')], delimiter=';')
                writer.writeheader()
                writer.writerows(rows)
            print(f'{len(rows)} Einträge exportiert: {args.output}')
        elif args.command == 'status':
            print(json.dumps([dict(r) for r in conn.execute('SELECT id,source_file,source_sha256,liturgical_year,parser_version,imported_at,report_json FROM import_runs')], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
