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

## Termine und Textformatierung

Die Navigation ist nach Arbeitsablauf angeordnet: Übersicht, Erstellen, Verkündigungen, Termine, Heilige, Vorlagen, Einstellungen. Jeder Eintrag hat ein Icon.

Unter **Termine** (`#/termine`) zeigt eine Tabelle die Inhalte mit internem Namen, Pfarren und Wochenzuordnungen. Neu und Bearbeiten öffnen ein Modal wie bei den Heiligen. Ein Termin hat einen internen Namen, ein formatiertes Inhaltsfeld, mindestens eine Pfarre und beliebig mehrere liturgische Wochen (auch aus mehreren Kirchenjahren). Datum, Uhrzeit und Ort werden nicht separat gepflegt. Beide Sprachen können im gemeinsamen Inhaltsfeld stehen. Ohne Wochenzuordnung bleibt der Termin als Entwurf gespeichert. Beim Vorbereiten einer Verkündigung werden passende Inhalte automatisch in den Abschnitt Termine übernommen; der interne Name wird nicht ausgegeben. Bereits gespeicherte Verkündigungen bleiben unabhängige Momentaufnahmen.

Textfelder für Hinweise, Intentionen, Titel und Ankündigungen unterstützen einzelne fette Wörter: Text markieren und **Fett** oder **Strg+B** drücken. Erneutes Umschalten macht die Auswahl normal. Vorbelegte fette Überschriften erlauben auch normal gesetzte Teilstücke. Texte werden mit validierten Formatierungsbereichen gespeichert, nicht als HTML. Beim ewigen Licht bleibt nur die Beschriftung automatisch fett; Namen sind standardmäßig normal.

Alle acht Tage werden angezeigt und ausgegeben, auch ohne Heilige, Messe oder Text. Nur **Diesen Tag ausgeben** auszuschalten entfernt einen Tag. Bereits erzeugte Word-Dateien müssen für diese Änderung neu erstellt werden.

## Vorgaben pro Pfarre

Unter **Einstellungen** (`#/einstellungen`) werden wiederkehrende Gottesdienste, Kanzleistunden und Kontakte getrennt nach Pfarre gespeichert. Jeder Gottesdienst hat einen Wochentag, eine optionale Uhrzeit, einen Ort und eine zweisprachige Bezeichnung. Mehrere Vorgaben für denselben Wochentag sind möglich. Deaktivierte Vorgaben werden nicht übernommen.

## Verkündigungen erstellen

Unter **Erstellen** (`#/erstellen`) Pfarre, Vorlage und liturgische Woche wählen. **Woche laden** erstellt acht Tage von Sonntag bis zum folgenden Sonntag und übernimmt die aktuellen Pfarrvorgaben, auch für beide Sonntage. Änderungen an Vorgaben verändern gespeicherte Entwürfe nicht.

Die Bearbeitung gliedert sich in **Gottesdienste & Heilige**, **Termine**, **Kontakte** und **Dokumentvorschau**. Beim Öffnen oder Aktualisieren der Vorschau wird der Entwurf gespeichert. Die Vorschau zeigt die tatsächlich erzeugte Word-Datei nach einer internen Konvertierung, einschließlich Bildern, Tabellen und Seitenumbrüchen. Microsoft Word oder LibreOffice wird nur für diese Vorschau benötigt. Änderungen machen die bisherige Vorschau ungültig.

**Verkündigung erstellen** speichert den aktuellen Stand und erzeugt eine bearbeitbare DOCX-Datei. **Word herunterladen** lädt diese Datei herunter. Dafür wird kein PDF-Konverter benötigt. Nach Änderungen muss die Word-Datei erneut erstellt werden. Die separate Seite **Verkündigungen** (`#/verkuendigungen`) zeigt gespeicherte Entwürfe mit Paging, Öffnen, Word-Download und bestätigtem Löschen. Der Browser speichert den aktuellen Entwurf zusätzlich lokal zwischen; diese Kopie ersetzt das Speichern auf dem Server nicht.

Aktive und verfügbare Heilige werden beim Laden neuer Wochen als sichtbare Titel übernommen, auch wahlweise Gedenktage. Bestehende Entwürfe behalten ihre Auswahl. Unter **Titelzeilen und Heilige** können eigene Zeilen wie Kirchtag und Erntedank ergänzt werden; jede Zeile erscheint als **Deutsch | Slowenisch**, standardmäßig fett. Einzelne Teile können über die Formatierung normal gesetzt werden. Messintentionen sind Gebetsanliegen mit optionalem Zeichen und Referenz; Hinweise sind zusätzliche Informationen.

Bei der alten Gurker Vorlage mit zwei übereinanderliegenden Vollbreiten-Bannern in einem schwebenden Textfeld wird nur die erzeugte Ausgabe bereinigt. Die Originaldatei bleibt unverändert. Kanzleistunden und Kontakte nutzen die Rahmen und Paragraphen der gewählten Vorlage; Kontakte werden links und rechts angeordnet.

## Verwaltungsfilter für liturgische Wochen

In der Heiligenverwaltung das Jahr auswählen und danach direkt neben dem Monat die liturgische Woche wählen. Die Zeiten sind als Gruppen in diesem einen Dropdown zusammengefasst. Die Optionen werden aus den datierten Überschriften des importierten Directoriums abgeleitet. Es werden keine ISO-Kalenderwochen verwendet. Der Zeitraum reicht jeweils vom zugehörigen Sonntag bis einschließlich des folgenden Sonntags. Für Weihnachtszeit, Karwoche und den Fastenbeginn werden benannte Zeiträume statt erfundener Wochennummern angeboten.

Bei einer Wochenauswahl wird ein vorheriger Monatsfilter zurückgesetzt, damit Wochen über eine Monatsgrenze vollständig erscheinen. Suche, Rang, Aktivierung und Verfügbarkeit lassen sich weiterhin kombinieren. Der Jahresfilter 2026/27 umfasst den 1. Dezember 2026 bis 30. November 2027. Er filtert nach dem Datum und kann deshalb Einträge aus zwei Directorien enthalten. Wochen werden mit dieser Jahresgrenze geschnitten. Die Monate werden von Dezember bis November angeboten. Lücken im Directorium werden nicht mit erfundenen Daten gefüllt.


## Gottesdienste und gemeinsame Sonntage

Unter `#/gottesdienste` werden Gottesdienste und Intentionen pro Pfarre und konkretem Datum gespeichert. Auch beim Speichern einer Verkündigung werden geänderte Gottesdienste dort hinterlegt. Neu vorbereitete Wochen laden diesen Stand, sodass der gemeinsame Sonntag benachbarter Wochen nur einmal gepflegt werden muss. Es erfolgt keine pauschale Wiederholung auf andere Sonntage. Regelmäßige Uhrzeiten stammen weiterhin aus den Einstellungen. Gespeicherte Dokumente bleiben Momentaufnahmen; veraltete Änderungen an einem Gottesdienst werden mit HTTP 409 abgefangen.

Die Erstellung trennt Gottesdienste/Heilige, Termine, Kontakte und Vorschau. Tage, einzelne Gottesdienste und die Konfigurationsbereiche unter Termine, Kontakte und Einstellungen starten eingeklappt. Das zusätzliche Gottesdienst-Textfeld entfällt. Kanzleistunden werden mit eigener Überschrift und normalen Zeiten ausgegeben.

Die Wochenzuordnung im Termin-Modal hat eine Textsuche und einen Filter für die liturgische Zeit. Die Auswahl bleibt auch bei gefilterter Liste erhalten. Formatierte Felder unterstützen Fett und Unterstreichen (Schaltflächen, Strg+B bzw. Strg+U).

Im Terminbereich einer Verkündigung zeigt die eingeklappte Zeile den internen Namen des übernommenen Termins. Das zusätzliche Titelfeld entfällt; im Dokument wird nur der Inhalt ausgegeben. Der interne Name bleibt in der Momentaufnahme erhalten, auch nach Löschen des verwalteten Termins. Einzelne Intentionen sind ebenfalls aufklappbar und starten immer geschlossen.


Gottesdienste werden beim Öffnen eines gespeicherten Entwurfs, bei Rückkehr zum Fenster/Reiter und unmittelbar vor Speichern/Erstellen frisch abgefragt. Unveränderte Gottesdienste werden im Entwurf aktualisiert. Lokale Änderungen an Gottesdiensten bleiben erhalten; bei abweichender Serverrevision wird das Speichern blockiert, bis der aktuelle Stand bewusst geladen wird. „Gottesdienste neu laden“ verwirft auf Wunsch ausschließlich diese Änderungen; übrige Inhalte bleiben bestehen. Die Gottesdienstverwaltung aktualisiert sich ebenfalls beim Fensterwechsel, ohne ungespeicherte Eingaben zu ersetzen.

Vorhandene Einträge starten eingeklappt. Neu angelegte Gottesdienste, Intentionen und Termine öffnen sich sofort und können anschließend normal zugeklappt werden.

Es gibt keine zeitgesteuerten Abfragen im Hintergrund. Änderungen aus der Gottesdienstverwaltung werden beim Öffnen oder Zurückwechseln in die Verkündigung und spätestens vor Speichern/Erstellen übernommen. Zusätzlich bleibt der manuelle Button zum Neuladen verfügbar.

Messintentionen werden in einem gemeinsamen Feld „Messintention / Namen“ ohne Sprachaufteilung bearbeitet. Historische Inhalte aus Deutsch und Slowenisch erscheinen zusammen untereinander, einschließlich vorhandener Fett- und Unterstreichungsbereiche. Änderungen speichern den gemeinsamen Inhalt als ein Textfeld.
