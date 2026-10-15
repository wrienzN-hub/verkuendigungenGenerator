# React Oberfläche

Das Frontend liegt in `frontend/` und verwendet React, TypeScript und Vite. Die Kopfzeile verlinkt auf die Übersicht und die Heiligenverwaltung. Die Übersicht ist vorbereitet; die Auswahl liturgischer Wochen und die PDF-Erzeugung folgen später.

## Start mit einem Server

Nach dem Frontend-Build stellt FastAPI die Oberfläche und REST-API gemeinsam unter http://127.0.0.1:8000 bereit. Auf diesem Rechner ist die Python-Umgebung bereits unter `.venv-api` eingerichtet.

```powershell
.\start.ps1
```

Wenn auf Port 8000 bereits eine API läuft, diese zuerst im zugehörigen Terminal mit `Strg+C` beenden oder einen anderen Port verwenden: `.\start.ps1 -Port 8001`. Die bereits laufende API muss nach dem ersten Frontend-Build einmal neu gestartet werden, damit sie die Oberfläche ebenfalls ausliefert.

Nach Codeänderungen das Frontend erneut bauen und den Server neu starten. Für eine neue Installation werden Python ab 3.12, Node.js ab 22.12 und pnpm benötigt:

```powershell
py -m venv .venv-api
.\.venv-api\Scripts\python.exe -m pip install -e ".[test]"
cd frontend
pnpm install --frozen-lockfile
pnpm build
cd ..
.\start.ps1
```

## Entwicklung

Für automatische Aktualisierung bei Änderungen zwei Terminals öffnen:

```powershell
# Terminal 1, Projektordner
.\.venv-api\Scripts\python.exe -m uvicorn verkuendigungen.api.app:app --reload --host 127.0.0.1 --port 8000
```

```powershell
# Terminal 2
cd frontend
pnpm dev
```

Vite zeigt die Entwicklungsadresse, normalerweise http://127.0.0.1:5173. Der Vite-Proxy leitet `/api` und `/health` an FastAPI weiter; zusätzliche CORS-Freigaben sind nicht nötig.

## Heiligenverwaltung

- Suche in beiden Sprachfeldern; die API berücksichtigt Unicode-Groß-/Kleinschreibung.
- Filter nach Kirchenjahr, Monat, Rang und Aktivierung. Ein weiterer Filter für liturgische Verfügbarkeit lässt sich einblenden.
- Paging mit Trefferzahl, Seitenauswahl und 10, 25, 50 oder 100 Einträgen pro Seite. Die Filterung erfolgt vor dem Paging auf dem Server.
- Direkter Schalter zum Aktivieren und Deaktivieren. Dies verändert nicht den fachlichen Status einer entfallenen oder örtlich bedingten Feier.
- Bearbeitungsdialog für Namen in beiden Sprachen, Rang, Verfügbarkeit, örtliche Bedingungen, Aktivierung.
- Originaltext, Quellenverweis, Datum und Kirchenjahr bleiben schreibgeschützt. Änderungen gelten nur für den vorhandenen Eintrag dieses Kirchenjahres.
- Lade-, Fehler- und Leerzustände, Speichermeldungen sowie Schutz vor versehentlichem Verwerfen ungespeicherter Änderungen. Der Dialog ist per Tastatur bedienbar; auf kleinen Bildschirmen lässt sich die Tabelle horizontal scrollen.

Die Oberfläche benötigt eine laufende API und verwendet echte SQLite-Daten. Sie enthält keine Beispieldaten als Ersatz bei Verbindungsfehlern. Es gibt weiterhin keine Benutzeranmeldung; der Server wird lokal an `127.0.0.1` gebunden.

## API Ergänzungen

`GET /api/v1/saints/page` liefert `{items, total, limit, offset}` und akzeptiert zusätzlich `month`, `rank` und `observance_status`. `GET /api/v1/saints/filters` liefert Kirchenjahre und Bestandszahlen. Der bestehende Listenendpunkt bleibt kompatibel.

`PATCH /api/v1/saints/{id}` erlaubt jetzt `name`, `name_sl`, `rank_code`, `observance_status`, `disabled` und `applicability_note`. Nur übermittelte Felder werden geändert. Leere Namen, ungültige Werte, unbekannte Felder und leere Änderungsobjekte werden abgelehnt. Quellenangaben können nicht überschrieben werden.

## Directorium hochladen

Die Schaltfläche „Directorium hochladen“ öffnet einen Dialog mit Dateiauswahl und Drag-and-drop. Nach dem erfolgreichen Import zeigt die Oberfläche automatisch die Einträge des erkannten Kirchenjahres. Gleiche Dateien erzeugen keine Duplikate. Fehler werden im Dialog angezeigt; vorhandene Directorien lassen sich dort als Original-PDF öffnen. Es gibt keinen Prüf- oder Freigabestatus.

Unterstützt werden PDF-Dateien bis 25 MB mit auswählbarem Text im Gurker Monats-/Tagesformat. Einzelne fehlende Kalendertage werden als Hinweis angezeigt und verhindern den Import nicht. Abweichende Layouts oder unlesbare Dateien werden weiterhin abgelehnt.

Fehlende Kalendertage verhindern den Import nicht, sofern mindestens 90 % des Kirchenjahres erkannt wurden. Der Importbericht enthält `missing_dates` (ISO-Daten) und `expected_calendar_days`. Die Oberfläche zeigt die Lücken nach dem Upload und dauerhaft bei den vorhandenen Directorien an. Für fehlende Tage entstehen keine erfundenen Feiern oder Quellenabschnitte.
