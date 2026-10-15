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
- HTTP 422: beschädigtes, verschlüsseltes, unlesbares oder nicht unterstütztes PDF; weitgehend nicht erkanntes Kalendarium oder falsche Wochentage.
- HTTP 409: eine andere Ausgabe für dasselbe Kirchenjahr ist bereits vorhanden.

```powershell
curl.exe -F "file=@resources/directorium-2026-27-kern_21092026.pdf" http://127.0.0.1:8000/api/v1/imports/directorium
```

`GET /api/v1/imports/{id}/source` liefert das gespeicherte Original-PDF. Die Liste `/api/v1/imports` enthält `has_source`, aber keine PDF-Binärdaten. Es gibt keine Prüfstatusfelder mehr.

Fehlende Kalendertage verhindern den Import nicht, sofern mindestens 90 % des Kirchenjahres erkannt wurden. Der Importbericht enthält `missing_dates` (ISO-Daten) und `expected_calendar_days`. Die Oberfläche zeigt die Lücken nach dem Upload und dauerhaft bei den vorhandenen Directorien an. Für fehlende Tage entstehen keine erfundenen Feiern oder Quellenabschnitte.

## Word-Vorlagen

`GET /api/v1/templates` liefert alle Vorlagen als Metadaten mit `id`, `parish_name`, `name`, `source_filename`, `file_size` und `created_at`.

`POST /api/v1/templates` speichert eine DOCX-Datei als Multipart-Upload mit den Feldern `file`, `parish_name` und `name` (jeweils 1–120 Zeichen). Pro Pfarre sind mehrere Vorlagen möglich; derselbe Name je Pfarre liefert HTTP 409. Erfolgreiche Uploads liefern HTTP 201 und die Metadaten. Maximalgröße: 25 MB (HTTP 413). Andere Dateiendungen liefern HTTP 415, ungültige oder verschlüsselte Word-Dateien HTTP 422. Makros werden nicht unterstützt.

`GET /api/v1/templates/{id}/source` lädt die unveränderte Originaldatei herunter; unbekannte IDs liefern HTTP 404. Die Datei wird gemeinsam mit ihren Metadaten in SQLite gespeichert und ist damit Bestandteil einer Datenbanksicherung.

Die React-Seite `#/vorlagen` bietet Upload, Pfarrfilter und Download. Unter `#/erstellen` können unterstützte Vorlagen befüllt und als DOCX ausgegeben werden.

## Verkündigungen

- `GET /api/v1/documents/options`: Kirchenjahre, Vorlagen einschließlich der eingebauten Eberndorfer Vorlage (ID 0), deren `supported`-Status und `preview_available` (installierter Konverter erkannt).
- `GET /api/v1/documents/weeks?year=2026%2F27`: Wochen des tatsächlichen importierten Kirchenjahres einschließlich des ersten Adventssonntags im November. Anders als der Verwaltungsfilter wird der Zeitraum nicht am 1. Dezember abgeschnitten.
- `POST /api/v1/documents/prepare`: `{ "template_id": 0, "year": "2026/27", "week_id": "advent:2026-11-29" }` liefert `{payload,warnings}` mit allen acht Tagen. Es wird noch nichts gespeichert. Deaktivierte, verdrängte und bedingte Feiern werden ausgelassen. Alle verfügbaren Feiern einschließlich wahlweiser Gedenktage und Kommemorationen sind als Titel sichtbar; sie können im Entwurf einzeln ausgeblendet werden.
- `POST /api/v1/documents`: `{payload}` speichert einen neuen Entwurf und eine unveränderliche Kopie der Word-Vorlage (HTTP 201). Die Antwort enthält `id`, `revision`, `payload`, `has_docx`, `has_pdf` (interne Vorschau), Zeitstempel.
- `GET /api/v1/documents?limit=20&offset=0`: paginierte Metadaten `{items,total}`. `GET /api/v1/documents/{id}` öffnet einen Entwurf.
- `PUT /api/v1/documents/{id}`: `{payload,revision}` ersetzt den bearbeiteten Inhalt. Vorlage, Wochenauswahl und Zeitraum bleiben fest. Änderungen erhöhen die Revision und entfernen frühere Word-Ausgaben und Vorschauen. Veraltete Revisionen liefern HTTP 409.
- `POST /api/v1/documents/{id}/generate?revision=1`: erzeugt nur die DOCX-Datei aus dem gespeicherten Stand und der gespeicherten Vorlage. Liefert `docx_url`; benötigt weder Word noch LibreOffice.
- `GET /api/v1/documents/{id}/docx`: Download der erzeugten Word-Datei; vor der Erstellung bzw. nach einer Änderung HTTP 404.
- `DELETE /api/v1/documents/{id}?revision=1`: löscht Entwurf und erzeugte Dateien. Eine inzwischen geänderte Revision liefert HTTP 409. Vorlage und Pfarrvorgaben bleiben erhalten.
- `POST /api/v1/documents/{id}/preview?revision=1`: rendert dieselbe DOCX-Datei mit Word/LibreOffice für eine layoutgetreue Vorschau. Liefert `preview_url`. Konvertierungsfehler liefern HTTP 503; Word-Ausgabe bleibt unabhängig möglich. Änderungen während der Konvertierung verhindern die Zuordnung einer veralteten Vorschau (HTTP 409).
- `GET /api/v1/documents/{id}/preview?revision=1`: interne Vorschau als inline dargestelltes PDF mit `Cache-Control: no-store`. Eine veraltete Revision liefert HTTP 409. Es gibt keinen PDF-Download in der Oberfläche.

## Pfarrvorgaben

`GET /api/v1/settings?parish=Eberndorf` liefert `{services,office_hours,contact}`. Für Pfarren ohne Vorgaben werden leere Listen und Kontakte geliefert. `PUT` auf denselben Endpunkt speichert diese Struktur transaktional. `services` entspricht dem Service-Modell des Dokument-Payloads, ergänzt um `weekday` (0 = Montag bis 6 = Sonntag). `enabled: false` deaktiviert eine Regel. Uhrzeiten und Kanzleistunden werden wie im Dokument validiert. Regeln gelten nur für neu geladene Wochen; neue IDs je Tag verhindern Konflikte bei beiden Sonntagen.

Die vollständigen validierten Payload-Modelle sind unter `/docs` und in `schemas/documents.py` dokumentiert. Ungültige Zeitangaben, doppelte IDs, abweichende Tage oder Wochenauswahlen liefern HTTP 422. Word-Makros und automatische Link-/Feldupdates sind bei der Konvertierung deaktiviert.

## Liturgische Wochen

`GET /api/v1/saints/weeks?year=2026%2F27` liefert die im Directorium erkennbaren Wochen mit `id`, `season`, `season_label`, `week`, `label`, `start` und `end`. Für benannte Zeiträume ohne Wochennummer ist `week` null. Fehlende Kirchenjahre liefern eine leere Liste.

`GET /api/v1/saints/page?year=2026%2F27&liturgical_week=advent%3A2026-11-29` wählt die erste Adventswoche (29. November bis 6. Dezember) und schneidet sie mit dem Jahresfilter; das Ergebnis beginnt daher frühestens am 1. Dezember. Die Woche muss zum angegebenen Kirchenjahr gehören; ungültige Kombinationen liefern HTTP 422. Ein zusätzlicher Datumsbereich wird mit dem Wochenzeitraum geschnitten. Andere Filter und Paging bleiben kombinierbar.

Für `/saints/page` und `/saints/weeks` bezeichnet `year=2026/27` den Zeitraum 01.12.2026–30.11.2027. Die Auswahl basiert auf Datumsgrenzen über alle importierten Directorien hinweg; die Quellenzuordnung `liturgical_year` der Datensätze bleibt erhalten. Der ältere Listenendpunkt `/saints` behält seinen Filter auf das Quellenkirchenjahr bei.
