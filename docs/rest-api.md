# REST API und Projektstruktur

Die Anwendung ist ein modularer Monolith mit FastAPI und SQLite. Kommandozeile und REST-API verwenden dieselbe Datenbanklogik. Docker ist für den lokalen Start nicht erforderlich.

```text
verkuendigungen/
  core/config.py                  Datenbankpfad und Konfiguration
  infrastructure/database.py      Verbindungen und Migrationen
  infrastructure/migrations/      Versioniertes SQL-Schema
  repositories/saints.py           Parametrisierte SQL-Abfragen
  services/directorium.py         Directorium-Import und Prüfungen
  schemas/saints.py                Validierte API-Ein- und Ausgaben
  api/app.py                      FastAPI-App und Startinitialisierung
  api/dependencies.py             Datenbankverbindung pro Anfrage
  api/routes/saints.py             Heilige auflisten, lesen und schalten
  api/routes/imports.py            Importbericht lesen
  cli.py                          Bestehende Kommandozeilenbefehle
tests/                            Import- und API-Tests
resources/                        Directorium, Word-Vorlage und JSON-Template
data/                             Befüllte Datenbank und Prüfexporte
```

Spätere Module für Kalenderwochen und Dokumente erhalten eigene Routen, Schemas, Services und Repositories. PDF- und Word-Erzeugung gehören in die Services. Die vollständige Vorrangberechnung, Dokumenterzeugung und Oberfläche sind noch nicht implementiert.

## Lokal starten

PowerShell im Projektordner öffnen. Python 3.12 oder neuer wird benötigt. Die separate Umgebung `.venv-api` vermeidet Konflikte mit einer bestehenden `.venv`.

```powershell
py -m venv .venv-api
.\.venv-api\Scripts\python.exe -m pip install -e ".[test]"
.\.venv-api\Scripts\python.exe -m uvicorn verkuendigungen.api.app:app --reload --host 127.0.0.1 --port 8000
```

Ist `.venv-api` bereits eingerichtet, genügt der letzte Befehl. `Strg+C` beendet den Server.

- Interaktive Dokumentation: http://127.0.0.1:8000/docs
- OpenAPI-Vertrag: http://127.0.0.1:8000/openapi.json
- Betriebsprüfung: http://127.0.0.1:8000/health

Standarddatenbank ist `data/verkuendigungen.sqlite3`. Beim Start werden fehlende Tabellen migriert; der PDF-Import erfolgt ausschließlich über die CLI. Ein anderer Pfad kann vor dem Start gesetzt werden:

```powershell
$env:VERKUENDIGUNGEN_DB = 'C:\Pfad\zur\verkuendigungen.sqlite3'
```

Die API ist für lokale Nutzung ohne Anmeldung vorgesehen. Vor einem Mehrbenutzerbetrieb sind Anmeldung und Zugriffsrechte zu ergänzen. Der lokale Start bindet an `127.0.0.1`.

## Endpunkte

| Methode | Pfad | Funktion |
| --- | --- | --- |
| GET | `/health` | Datenbankverbindung prüfen |
| GET | `/api/v1/saints` | Heilige und weitere Feiern filtern |
| GET | `/api/v1/saints/{id}` | Einzelnen Datensatz lesen |
| PATCH | `/api/v1/saints/{id}` | Bezeichnungen, Rang, Status und Notizen bearbeiten |
| GET | `/api/v1/saints/page` | Gefilterte Seite einschließlich Trefferzahl |
| GET | `/api/v1/saints/filters` | Kirchenjahre und Bestandszahlen |
| GET | `/api/v1/imports` | Importläufe samt Bericht lesen |

Die Liste unterstützt `start`, `end` (ISO-Datum), `year` (z. B. `2026/27`), `search`, `disabled`, `available_only`, `limit` und `offset`. Standardmäßig zeigt sie die ersten 100 Verwaltungseinträge einschließlich entfallener oder deaktivierter Feiern. `limit` ist auf 1000 begrenzt. Weitere Ergebnisse lassen sich über `offset` laden. `search` sucht wörtliche Teilzeichenfolgen in beiden Sprachen und ignoriert über Unicode-Casefolding die Groß-/Kleinschreibung. Der neue Endpunkt `/page` bietet zusätzlich Monats-, Rang- und Verfügbarkeitsfilter; siehe [frontend.md](frontend.md).

Für die spätere Wochenansicht `available_only=true` verwenden. Dies schließt deaktivierte, entfallene und örtlich bedingte Feiern aus. Optionale Feiern bleiben Auswahlmöglichkeiten.

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/saints?start=2026-11-29&end=2026-12-06&available_only=true'

Invoke-RestMethod -Method Patch `
  -Uri 'http://127.0.0.1:8000/api/v1/saints/5' `
  -ContentType 'application/json' `
  -Body '{"disabled": true}'
```

`disabled` ist in Antworten immer `true` oder `false`. Schreibanfragen akzeptieren ausschließlich echte JSON-Booleans; Zahlen wie `1` oder Zeichenfolgen werden abgelehnt. Zusätzlich bearbeitbare Felder sind in [frontend.md](frontend.md) dokumentiert. Unbekannte Felder und ungültige Datumsbereiche liefern HTTP 422; fehlende Datensätze HTTP 404.

Import und Tests:

```powershell
.\.venv-api\Scripts\python.exe -m verkuendigungen import-directorium
.\.venv-api\Scripts\python.exe -m unittest discover -s tests -v
```

## Directorium Upload

`POST /api/v1/imports/directorium` nimmt ein PDF als Multipart-Feld `file` an. Maximalgröße: 25 MB. Das Kirchenjahr wird aus dem Dokument erkannt. Erfolgreicher neuer Import: HTTP 201; bereits vorhandene identische Datei: HTTP 200. Die Antwort enthält Import-ID, Kirchenjahr, Zeitraum, Anzahl der Kalendertage und Feiern sowie `already_imported`.

- HTTP 413: Datei zu groß.
- HTTP 415: keine PDF-Dateiendung.
- HTTP 422: beschädigtes, verschlüsseltes, unlesbares oder nicht unterstütztes PDF; unvollständiges Kalendarium oder falsche Wochentage.
- HTTP 409: eine andere Ausgabe für dasselbe Kirchenjahr ist bereits vorhanden.

```powershell
curl.exe -F "file=@resources/directorium-2026-27-kern_21092026.pdf" http://127.0.0.1:8000/api/v1/imports/directorium
```

`GET /api/v1/imports/{id}/source` liefert das gespeicherte Original-PDF. Die Liste `/api/v1/imports` enthält `has_source`, aber keine PDF-Binärdaten. Es gibt keine Prüfstatusfelder mehr.
