# Datenbank und Directorium Import

## Vorhandener Datenbestand

`data/verkuendigungen.sqlite3` ist eine befüllte lokale SQLite-Datenbank für die Diözese Gurk, Kirchenjahr `2026/27`. Sie benötigt keinen separaten Datenbankserver, keine Zugangsdaten und keine laufende Internetverbindung. Python 3.12 oder neuer und das in `pyproject.toml` festgelegte `pypdf` reichen für den Import aus. Die Anwendung selbst nutzt für SQLite die Python-Standardbibliothek.

Importquelle ist `resources/directorium-2026-27-kern_21092026.pdf`. Die 377 Datensätze stehen für liturgische Feiern, nicht für 377 einzelne Personen: gemeinsam gefeierte Heilige bleiben wie im Directorium in einem Eintrag. Auch Herrenfeste, Marienfeiern und Sonntage werden benötigt, um die spätere Wochenansicht zu füllen.

| Status | Anzahl | Bedeutung |
| --- | ---: | --- |
| `observed` | 154 | Im Tagesabschnitt angesetzte Feier |
| `optional` | 162 | Nichtgebotener Gedenktag, als Auswahl verfügbar |
| `commemoration_only` | 16 | Laut Offizium nur Kommemoration möglich |
| `suppressed` | 42 | In diesem Jahr entfallen bzw. verdrängt |
| `conditional` | 3 | Nur unter örtlichen Bedingungen zu verwenden |

Alle 364 Tage vom 29. November 2026 bis 27. November 2027 sind hinterlegt. Am 25. Oktober enthält die Quelle zwei Alternativen: Kirchen mit unbekanntem und Kirchen mit bekanntem Weihetag. Deshalb gibt es 365 Quellenabschnitte. Alle 227 PDF-Seiten sind zusätzlich als extrahierter Originaltext in der Datenbank gespeichert.

## Tabellen und Felder

`saints` enthält die für die Verkündigung benötigten Heiligen und weiteren Feiern:

| Feld | Zweck |
| --- | --- |
| `id` | Stabile ID innerhalb dieser Datenbank, später `source_celebration_id` im Dokument-JSON |
| `liturgical_year`, `celebration_date` | Kirchenjahr und konkretes Datum dieses Jahres |
| `name`, `name_sl` | Deutscher Titel und vorhandene slowenische Bezeichnung; fehlendes Slowenisch bleibt `NULL` |
| `kind` | Grobe Inhaltskategorie: Heiliger, Marienfeier, Sonntag oder Fest |
| `rank_code` | Rang aus der Quelle: `H`, `F`, `G`, `g`; zusätzliche Kategorien für Sonntage, Triduum und Oktaven |
| `calendar_scope` | Explizite Kürzel wie `RK`, `DK`, `ÖBK` oder `GK`; sonst `unspecified` |
| `observance_status` | Feier, Wahlgedenktag, Kommemoration, entfallen oder örtlich bedingt |
| `applicability_note` | Bedingung oder Erläuterung; insbesondere bei örtlichen Sonderfällen |
| `disabled` | Manueller Schalter; gilt für diesen Eintrag dieses Kirchenjahres |
| `source_block_id`, `calendar_day_id` | Bezug zum Quellenabschnitt und Kalendertag |
| `source_key` | Eindeutiger Schlüssel aus Quellenhash, Datum, Variante und Position |
| `source_page`, `source_reference`, `source_text` | PDF-Seite, lesbare Fundstelle und extrahierte Bezeichnung |
| `review_status`, `review_notes` | Fachlicher Prüfstatus und konkrete Auffälligkeiten |
| `updated_at` | Zeitpunkt der letzten Änderung in UTC |

Die Kategorie `kind` ist eine Suchhilfe, keine verbindliche theologische Einordnung. Für Auswahl und Vorrang sind Kalender, Rang und Status maßgeblich. Bei entfallenen Feiern, die in der Quelle ohne Rang genannt werden, bleibt `rank_code` `NULL`; ein Rang wird nicht erfunden.

Weitere Tabellen:

- `calendar_days`: jeder Kalendertag mit Kirchenjahr und Wochentag. Liturgische Wochennummern werden nicht gespeichert.
- `source_day_blocks`: datierte Originalabschnitte einschließlich Varianten, Überschrift, Hinweisen und vollständigem extrahiertem Text. Hier bleiben auch Lesungen, liturgische Farben und weitere Rubriken erhalten, ohne sie bereits als eigene strukturierte Felder zu behaupten. Übergangstexte zwischen Tagesabschnitten können zum vorherigen Abschnitt gehören; die vollständigen Seiten ermöglichen die genaue Nachprüfung.
- `source_pages`: vollständiger Text jeder PDF-Seite mit physischer und, falls erkannt, gedruckter Seitennummer.
- `import_runs`: Quelle, SHA-256-Prüfsumme, Parser-Version, Kirchenjahr, Importzeit, Status und Bericht.

`available_celebrations` ist eine SQL-View für nicht deaktivierte Feiern mit Status `observed`, `optional` oder `commemoration_only`. Optionale Gedenktage sind dabei Auswahlmöglichkeiten, keine Anweisung, alle gleichzeitig zu feiern. Entfallene und örtlich bedingte Feiern erscheinen nur in der vollständigen Verwaltungsabfrage. Ein manuelles Aktivieren eines entfallenen Eintrags hebt dessen liturgischen Status nicht auf.

## Bedienung

Im Projektordner ausführen:

```powershell
python -m pip install -e .
python -m verkuendigungen init
python -m verkuendigungen import-directorium
python -m verkuendigungen status
python -m verkuendigungen list --start 2026-11-29 --end 2026-12-06
python -m verkuendigungen list --start 2026-11-29 --end 2026-12-06 --all
python -m verkuendigungen disable 1
python -m verkuendigungen enable 1
python -m verkuendigungen export data/heilige-2026-27.csv
```

Die Nummer bei `disable` und `enable` ist die ID aus der Liste. Einen anderen Datenbankpfad vor dem Unterbefehl setzen:

```powershell
python -m verkuendigungen --db data/test.sqlite3 import-directorium
```

Der gleiche PDF-Hash wird nur einmal importiert. Ein erneuter Aufruf erhält IDs, Prüfnotizen und den Aktivierungsstatus. Eine andere Datei desselben Kirchenjahres wird nicht automatisch über vorhandene Daten geschrieben. Der Parser ist durch Prüfsumme und Strukturprüfungen auf die vorliegende Ausgabe begrenzt. Ein neues Directorium benötigt eine überprüfte Importanpassung.

Schemaänderungen erfolgen über `verkuendigungen/infrastructure/migrations/` und die SQLite-Schemaversion `PRAGMA user_version`. Fremdschlüssel sind in jeder Anwendungsverbindung aktiviert. Der Import erfolgt in einer Transaktion; bei einem Fehler werden keine halben Importläufe gespeichert. Zur Sicherung reicht bei geschlossener Anwendung eine Kopie der SQLite-Datei. CSV und Importbericht sind Prüfexporte; die Datenbank ist der maßgebliche Datenbestand.

## Prüfung und Grenzen

Zehn automatisierte Tests prüfen den vollständigen Datumsbereich, Quellenumfang, Fremdschlüssel, wiederholten Import, Statusänderungen, mehrteilige Titel, entfallene und örtlich bedingte Feiern sowie ausgewählte Festtermine. Ausgewählte PDF-Seiten wurden zusätzlich visuell mit der Extraktion verglichen. Eine fachliche Prüfung sämtlicher Daten wird dadurch nicht ersetzt; sämtliche Einträge bleiben zunächst `needs_review`.

Bekannte Quellauffälligkeiten:

- Umschlag und Jahresübersicht unterscheiden sich beim Sonntagslesejahr (`A`/`B`). Dieses Feld wird deshalb nicht ungeprüft als Stammdatum gesetzt.
- Die Übersicht auf PDF-Seite 4 enthält für Fronleichnam und Herz Jesu widersprüchliche Termine. Übernommen sind die Tagesabschnitte am 27. Mai bzw. 4. Juni 2027.
- Scholastika ist am Aschermittwoch als `G` genannt, ohne ausdrücklichen Entfallvermerk. Der Eintrag ist als verdrängt markiert und zur fachlichen Prüfung kommentiert.
- Die slowenische Bezeichnung von Theresia Benedicta enthält eine auffällige extrahierte Zeichenfolge. Sie ist im Datensatz markiert; der Originaltext wird nicht stillschweigend durch eine erfundene Übersetzung ersetzt.
- Für den Pfingstmontag, das Domweihfest und Kirchen ohne bekannten Weihetag bleiben örtliche Bedingungen explizit gespeichert.

Es gibt noch keine vollständige Vorrangberechnung, keine automatische Übersetzung und keine Web-Oberfläche. Die spätere Wochenansicht kann bereits über den Datumsbereich auf diese Daten zugreifen. Eine Tabelle für Dokument-JSON wird erst mit dem Dokumentmodul ergänzt.

Tests starten:

```powershell
python -m unittest discover -s tests -v
```
