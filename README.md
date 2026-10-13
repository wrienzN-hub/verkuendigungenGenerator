# Verkündigungen-Generator

Ein Generator für kirchliche Verkündigungen. Später erstellt die Anwendung für eine gewählte Woche des Kirchenjahres ein Word-Dokument auf Basis einer austauschbaren Vorlage. Das Dokument enthält die Gottesdienste am Sonntag sowie die Heiligen und Gedenktage der betreffenden Woche.

Der erste Meilenstein ist bewusst schlank: Die Heiligen und Gedenktage aus dem Directorium werden zuverlässig in eine Datenbank übernommen und können aktiviert bzw. deaktiviert werden. Die spätere Dokumenterzeugung, Bearbeitungsoberfläche und eine KI-gestützte Vorlagenerkennung bauen darauf auf.

## Zielbild

1. Das System importiert die Heiligen und Gedenktage der Diözese Gurk aus dem Directorium.
2. Mitarbeitende können jeden Heiligen aktivieren oder deaktivieren.
3. Später wählen Mitarbeitende ein Kirchenjahr und eine liturgische Woche.
4. Das System ermittelt die Einträge der Woche, füllt eine Word-Vorlage und erzeugt eine `.docx`-Datei.

## Abgrenzung der Basisversion (MVP)

Im ersten Schritt enthalten:

- Einmaliger, kontrollierter Import der Heiligen aus dem Directorium im Ordner `resources/`.
- Speicherung der geprüften Heiligen in einer lokalen Datenbank.
- Berücksichtigung von deaktivierten Heiligen (`disabled`).
- Eine einfache Verwaltungsansicht bzw. API zum Aktivieren und Deaktivieren einzelner Heiligen.

Noch nicht Teil des ersten Schritts:

- Auswahl von Kirchenjahr und liturgischer Woche.
- Auslesen und Darstellung von Sonntagsmessen.
- Erstellung und Download einer Word-Datei.
- Browser-Oberfläche zum Bearbeiten von Texten oder Tabellenzeilen.
- Benutzerverwaltung, Rollen und Freigabeprozess.
- Vollautomatische, ungeprüfte Erkennung von PDF-Inhalten.
- Training eines neuronalen Netzes.

## Fachliche Annahmen und offene Punkte

Die Anwendung ist ausschließlich für die Diözese Gurk vorgesehen. Die vorhandene Quelle ist `resources/directorium-2026-27-kern_21092026.pdf`.

Liturgische Wochen werden nicht in der Datenbank gespeichert. Sobald die Dokumenterzeugung umgesetzt wird, berechnet das System die Woche aus dem konkreten Datum und den Regeln des liturgischen Kalenders. Das liturgische Jahr beginnt dabei am ersten Adventsonntag, also nicht stets am 1. Dezember. Dieser Sonntag liegt je nach Jahr zwischen dem 27. November und dem 3. Dezember.

Für eine verlässliche Zuordnung der Heiligen werden pro Eintrag mindestens das konkrete Datum und die liturgische Priorität gespeichert. Das ist wichtig, weil bewegliche Feste und Hochfeste gewöhnliche Gedenktage verdrängen können.

Vor der Umsetzung sind mit der Fachseite zu klären:

- Welche Angaben in der Sonntagsmesse erscheinen sollen (Messzeit, Ort, Intention, Lesungen usw.).
- Ob eine Änderung an einem Heiligen nur für ein Kirchenjahr oder dauerhaft gelten soll.

## Empfohlener Technologiestack

Für dieses Projekt empfehle ich einen modularen Monolithen: ein Backend, eine kleine Datenbank und später eine Web-Oberfläche. Das ist für den MVP deutlich wartbarer als getrennte Microservices und lässt sich bei Bedarf erweitern.

| Bereich | Empfehlung | Zweck |
| --- | --- | --- |
| Backend | Python 3.12 + FastAPI | Klare HTTP-API, Datenvalidierung und guter Zugriff auf Dokument- und PDF-Werkzeuge. |
| Datenzugriff | SQLAlchemy 2 + Alembic | Datenmodell und nachvollziehbare Datenbank-Migrationen. |
| Datenbank | SQLite im MVP, PostgreSQL im Betrieb | Einfacher lokaler Start; später sicherer Mehrbenutzerbetrieb. |
| Word-Erzeugung | `docxtpl` + `python-docx` | Platzhalter und Tabellen der Word-Vorlage zuverlässig füllen. |
| PDF-Import | PyMuPDF oder `pdfplumber` | Rohtext/Positionen aus dem Directorium extrahieren; Import wird fachlich geprüft. |
| Oberfläche (später) | React + TypeScript + Vite | Schnelle, gut wartbare Bearbeitungsoberfläche. |
| Tests | pytest + Playwright | Regeln und Word-Erzeugung automatisch testen. |
| Bereitstellung | Docker Compose | Reproduzierbarer Betrieb mit API, Datenbank und später Web-App. |

Python ist hier besonders passend, weil sowohl Word-Erzeugung als auch PDF-Auswertung in einem Backend stattfinden. Ein neuronales Netz ist für die erste Vorlagenerkennung nicht nötig: Eine Word-Vorlage mit klar benannten Platzhaltern ist robuster, nachvollziehbar und deutlich günstiger zu warten.

## Architektur

```text
Directorium-PDF --> Import/Prüfung --> Datenbank
                                     |
Auswahl Kirchenjahr + Woche --> FastAPI --> Word-Renderer --> .docx-Download
                                     |
                              spätere React-Oberfläche
```

Der Renderer erhält ausschließlich strukturierte Daten und eine dokumentierte Vorlage. Er sollte nie direkt aus dem PDF erzeugen. So bleiben PDF-Import und Dokumenterstellung unabhängig testbar.

## Datenmodell (Vorschlag)

| Tabelle | Wichtige Felder | Zweck |
| --- | --- | --- |
| `saints` | `id`, `name`, `celebration_date`, `rank`, `disabled`, `source_reference` | Heilige/Gedenktage der Diözese Gurk und ihre Aktivierung. |
| `import_runs` | `id`, `source_file`, `imported_at`, `status` | Nachvollziehbare Importe des Directoriums. |
| `document_payloads` (später) | `id`, `liturgical_date`, `payload_json`, `created_at`, `updated_at` | Das gesamte anpassbare JSON für ein zu erzeugendes Dokument. |

Wichtig: `disabled` ist kein Löschen. Deaktivierte Einträge bleiben nachvollziehbar in der Datenbank, werden später aber nicht im Dokument ausgegeben. Für Dokumente werden später keine einzelnen `row_overrides` gespeichert; stattdessen liegt der gesamte bearbeitbare Dokumentinhalt in einem JSON-Feld (`payload_json`).

## Temporäre Übergabedaten und Word-Vorlage

Sobald die Word-Erzeugung beginnt, erhält der Word-Renderer die Daten zunächst als JSON-Objekt. Dieses Objekt wird später als Ganzes in der Datenbank gespeichert (`payload_json`) und kann dort nachträglich bearbeitet werden. Separate Tabellen für einzelne Dokumentzeilen sind nicht vorgesehen. Die endgültige Feldstruktur wird gemeinsam mit der Vorlage festgelegt.

Beispiel für den vorläufigen Vertrag:

```json
{
  "year": "2026/27",
  "week": 12,
  "week_date_range": "16. - 22. Februar 2027",
  "events": [
    {
      "date": "2027-02-21",
      "type": "sunday_mass",
      "title": "7. Sonntag im Jahreskreis",
      "time": "10:00",
      "location": "Dom zu Gurk",
      "enabled": true
    }
  ],
  "saints": [
    {
      "date": "2027-02-22",
      "name": "Kathedra Petri",
      "rank": "Fest",
      "enabled": true
    }
  ]
}
```

`enabled: false` wird vom Renderer nicht ausgegeben. In der späteren Anwendung wird dieses Objekt aus der Datenbank zusammengestellt; die Word-Erzeugung selbst bleibt unverändert.

Die künftige `.docx`-Vorlage soll ohne Programmcode austauschbar sein. Empfohlen sind eindeutige Platzhalter, etwa:

```text
{{ church_year }}
{{ week_number }}
{{ week_date_range }}
{{ sunday_masses }}
{{ saints }}
```

Für Tabellen verwendet `docxtpl` Schleifen, beispielsweise für alle Heiligen einer Woche. Sobald eine Vorlage vorhanden ist, wird sie als Version unter `resources/templates/` abgelegt und mit mindestens einer Beispieldatei getestet.

## Import der Heiligen aus dem Directorium

Der PDF-Import wird in zwei Phasen umgesetzt:

1. Ein Importskript extrahiert Datum, Name, Rang, gegebenenfalls Region und Seitenreferenz in eine Staging-Tabelle bzw. CSV-Datei.
2. Ein Mensch prüft die Daten, korrigiert Erkennungsfehler und bestätigt erst dann den Import in `saints`.

Die Seitenreferenz und der Quell-Dateiname bleiben erhalten. Damit kann jeder Datensatz später auf seine Quelle zurückgeführt werden. Bei einem neuen Directorium wird ein neuer Importlauf angelegt statt alter Daten unbemerkt zu überschreiben.

## Umsetzungsschritte

1. Datenbank-Migrationen für `saints` und `import_runs` erstellen.
2. Importwerkzeug für das Directorium bauen und die extrahierten Heiligen fachlich prüfen.
3. Verwaltungsansicht bzw. API zum Auflisten sowie Aktivieren/Deaktivieren der Heiligen umsetzen.
4. Erst bei Vorliegen der Word-Vorlage die endgültige JSON-Struktur und Platzhalter festlegen.
5. Dann den Word-Renderer implementieren, der das vollständige JSON-Objekt verarbeitet.
6. Anschließend die Berechnung der liturgischen Woche aus einem Datum sowie Sonntagsmessen ergänzen.

## Spätere Bearbeitungsoberfläche

Die Oberfläche wird mindestens diese Seiten enthalten:

| Seite | Funktion |
| --- | --- |
| Dokument erstellen | Später: Datum bzw. Kirchenjahr und Woche wählen, JSON-Inhalt prüfen/anpassen und Word-Datei generieren. |
| Heilige verwalten | Alle Heiligen mit Datum, Rang und aktuellem Status anzeigen; jeden Eintrag einzeln per Schalter aktivieren oder deaktivieren. |
| Dokument bearbeiten | Später das gesamte gespeicherte JSON eines Dokuments anpassen. |

Die Seite **Heilige verwalten** schreibt nur den dauerhaften Status `disabled` eines Eintrags. Deaktivierte Heilige bleiben gespeichert, erscheinen jedoch nicht mehr in neu generierten Dokumenten. Eine Filterung nach Kirchenjahr, Monat, aktiv/deaktiviert und eine Suche nach Name sollten vorgesehen werden.

## KI / neuronales Netz (spätere Ausbaustufe)

Ein Training ist erst sinnvoll, wenn genügend gelabelte Beispielvorlagen und korrekte Ziel-Daten existieren. Für den Start wird eine regelbasierte Zuordnung mit Word-Platzhaltern verwendet. Falls später unterschiedliche, nicht standardisierte Vorlagen eingelesen werden sollen, kann eine KI beim Erkennen von Tabellenbereichen und Überschriften helfen. Die KI sollte dabei Vorschläge liefern, die ein Mensch bestätigt; sie sollte keine liturgischen Daten eigenständig erfinden.

## Qualitäts- und Datenschutzanforderungen

- Generierte Dateien nur für berechtigte Personen bereitstellen.
- Keine personenbezogenen Messintentionen ohne geregelte Zugriffsrechte speichern.
- Importfehler sichtbar machen und dokumentieren.
- Jede Vorlage und jede Datenänderung versionierbar halten.
- Für jedes Kirchenjahr mindestens einen fachlichen Abnahmetest durchführen.

## Nächster konkreter Schritt

Der nächste konkrete Schritt ist der Import der Heiligen aus dem vorhandenen Directorium in die Datenbank. Die Word-Vorlage, die JSON-Struktur für Dokumente und die Berechnung von Wochen folgen erst danach.
