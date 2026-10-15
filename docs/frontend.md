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

## Pfarrvorgaben

Unter **Einstellungen** (`#/einstellungen`) werden wiederkehrende Gottesdienste, Kanzleistunden und Kontakte getrennt nach Pfarre gespeichert. Jeder Gottesdienst hat einen Wochentag, eine optionale Uhrzeit, einen Ort und eine zweisprachige Bezeichnung. Mehrere Vorgaben für denselben Wochentag sind möglich. Deaktivierte Vorgaben werden nicht übernommen.

## Verkündigungen erstellen

Unter **Erstellen** (`#/erstellen`) Pfarre, Vorlage und liturgische Woche wählen. **Woche laden** erstellt acht Tage von Sonntag bis zum folgenden Sonntag und übernimmt die aktuellen Pfarrvorgaben, auch für beide Sonntage. Änderungen an Vorgaben verändern gespeicherte Entwürfe nicht.

Die Bearbeitung gliedert sich in **Gottesdienste & Heilige**, **Termine & Kontakt** und **Dokumentvorschau**. Beim Öffnen oder Aktualisieren der Vorschau wird der Entwurf gespeichert. Die Vorschau zeigt die tatsächlich erzeugte Word-Datei nach einer internen Konvertierung, einschließlich Bildern, Tabellen und Seitenumbrüchen. Microsoft Word oder LibreOffice wird nur für diese Vorschau benötigt. Änderungen machen die bisherige Vorschau ungültig.

**Verkündigung erstellen** speichert den aktuellen Stand und erzeugt eine bearbeitbare DOCX-Datei. **Word herunterladen** lädt diese Datei herunter. Dafür wird kein PDF-Konverter benötigt. Nach Änderungen muss die Word-Datei erneut erstellt werden. Die separate Seite **Verkündigungen** (`#/verkuendigungen`) zeigt gespeicherte Entwürfe mit Paging, Öffnen, Word-Download und bestätigtem Löschen. Der Browser speichert den aktuellen Entwurf zusätzlich lokal zwischen; diese Kopie ersetzt das Speichern auf dem Server nicht.

Aktive und verfügbare Heilige werden beim Laden neuer Wochen als sichtbare Titel übernommen, auch wahlweise Gedenktage. Bestehende Entwürfe behalten ihre Auswahl. Unter **Titelzeilen und Heilige** können eigene Zeilen wie Kirchtag und Erntedank ergänzt werden; jede Zeile erscheint als **Deutsch | Slowenisch** vollständig fett. Messintentionen sind Gebetsanliegen mit optionalem Zeichen und Referenz; Hinweise sind normale Zusatzinformationen.

Bei der alten Gurker Vorlage mit zwei übereinanderliegenden Vollbreiten-Bannern in einem schwebenden Textfeld wird nur die erzeugte Ausgabe bereinigt. Die Originaldatei bleibt unverändert. Kanzleistunden und Kontakte nutzen die Rahmen und Paragraphen der gewählten Vorlage; Kontakte werden links und rechts angeordnet.

## Verwaltungsfilter für liturgische Wochen

In der Heiligenverwaltung das Jahr auswählen und danach direkt neben dem Monat die liturgische Woche wählen. Die Zeiten sind als Gruppen in diesem einen Dropdown zusammengefasst. Die Optionen werden aus den datierten Überschriften des importierten Directoriums abgeleitet. Es werden keine ISO-Kalenderwochen verwendet. Der Zeitraum reicht jeweils vom zugehörigen Sonntag bis einschließlich des folgenden Sonntags. Für Weihnachtszeit, Karwoche und den Fastenbeginn werden benannte Zeiträume statt erfundener Wochennummern angeboten.

Bei einer Wochenauswahl wird ein vorheriger Monatsfilter zurückgesetzt, damit Wochen über eine Monatsgrenze vollständig erscheinen. Suche, Rang, Aktivierung und Verfügbarkeit lassen sich weiterhin kombinieren. Der Jahresfilter 2026/27 umfasst den 1. Dezember 2026 bis 30. November 2027. Er filtert nach dem Datum und kann deshalb Einträge aus zwei Directorien enthalten. Wochen werden mit dieser Jahresgrenze geschnitten. Die Monate werden von Dezember bis November angeboten. Lücken im Directorium werden nicht mit erfundenen Daten gefüllt.
