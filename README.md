# Verkündigungen Generator

Die Anwendung verwaltet Heilige und liturgische Feiern der Diözese Gurk. Ziel ist die Erstellung zweisprachiger Verkündigungen als PDF auf Grundlage einer austauschbaren Word-Vorlage.

## Vorhandene Funktionen

- React-Oberfläche mit Startseite und Heiligenverwaltung.
- Suche, Filter, Paging, Bearbeitung von Namen und Rang sowie Aktivierung und Deaktivierung.
- Directorium als PDF hochladen und automatisch in SQLite importieren.
- Automatische Erkennung des Kirchenjahres, Quellenarchiv und Schutz vor doppelten Importen.
- 377 liturgische Einträge für die 364 Tage des Kirchenjahres 2026/27 sind bereits enthalten.
- FastAPI-REST-API und Kommandozeilenverwaltung nutzen denselben Datenbestand.

Es gibt keinen manuellen Prüf- oder Freigabestatus. Die technischen Importprüfungen für Datum, Vollständigkeit und Datenbankkonsistenz bleiben bestehen.

## Starten

Nach dem Frontend-Build genügt im Projektordner:

```powershell
.\start.ps1
# Falls Port 8000 belegt ist:
.\start.ps1 -Port 8001
```

Die Oberfläche läuft dann unter `http://127.0.0.1:8000` bzw. dem gewählten Port. Docker ist nicht erforderlich. Eine neue Installation benötigt Python ab 3.12, Node.js ab 22.12 und pnpm:

```powershell
py -m venv .venv-api
.\.venv-api\Scripts\python.exe -m pip install -e ".[test]"
cd frontend
pnpm install --frozen-lockfile
pnpm build
cd ..
.\start.ps1
```

## Directorium importieren

In der Heiligenverwaltung auf **Directorium hochladen** klicken und ein PDF auswählen. Unterstützt werden Directorien der Diözese Gurk mit lesbarem Text, einer Kirchenjahresangabe und Monats-/Tagesabschnitten wie in der vorhandenen Ausgabe. Die Obergrenze beträgt 25 MB. Scans ohne Textebene und abweichende Layouts werden mit einer Fehlermeldung abgelehnt.

Der Import ermittelt den Zeitraum vom ersten Adventssonntag bis zum Samstag vor dem nächsten Kirchenjahr und prüft die erkannten Kalendertage auf passende Wochentage. Dieselbe Datei wird nur einmal importiert. Eine andere Datei für dasselbe Kirchenjahr überschreibt keine bestehenden Änderungen. Die Originaldatei bleibt in der Datenbank gespeichert.

Alternativ über die CLI:

```powershell
.\.venv-api\Scripts\python.exe -m verkuendigungen import-directorium --source resources/directorium-2026-27-kern_21092026.pdf
.\.venv-api\Scripts\python.exe -m verkuendigungen list --start 2026-11-29 --end 2026-12-06
```

## Aufbau und Dokumentation

Die Anwendung ist ein modularer Monolith: HTTP-Routen und Pydantic-Schemas, Importservices, SQL-Repositories und Datenbankmigrationen sind getrennt. SQLite benötigt keinen Server. Die API-Dokumentation steht unter `/docs` bereit.

- [Oberfläche und Entwicklungsbetrieb](docs/frontend.md)
- [REST-API](docs/rest-api.md)
- [Datenbank und Import](docs/datenbank.md)
- [Geplanter Dokumentablauf und JSON-Vertrag](docs/dokumentablauf.md)
- [JSON-Template](resources/templates/document-payload.template.json)

## Nächste Ausbaustufe

Mitarbeitende wählen ein Kirchenjahr, eine liturgische Zeit und deren Woche, beispielsweise „2026/27 → Advent → 1. Woche“. Die Anwendung lädt die Feiern vom ersten bis einschließlich des folgenden Sonntags. Anschließend lassen sich Gottesdienste, Orte, Zeiten, Messintentionen und Termine ergänzen. Das vollständige Dokument wird als JSON gespeichert und über die Word-Vorlage nach PDF ausgegeben. Wochenauswahl und Dokumenterzeugung sind noch nicht implementiert.

## Tests

```powershell
.\.venv-api\Scripts\python.exe -m unittest discover -s tests -v
cd frontend
pnpm build
pnpm format:check
```

Fehlende Kalendertage verhindern den Import nicht, sofern mindestens 90 % des Kirchenjahres erkannt wurden. Der Importbericht enthält `missing_dates` (ISO-Daten) und `expected_calendar_days`. Die Oberfläche zeigt die Lücken nach dem Upload und dauerhaft bei den vorhandenen Directorien an. Für fehlende Tage entstehen keine erfundenen Feiern oder Quellenabschnitte.
