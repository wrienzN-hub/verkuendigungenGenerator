# Datenbank und Directorium Import

## Datenbestand

`data/verkuendigungen.sqlite3` ist eine lokale SQLite-Datenbank für die Diözese Gurk. Das vorhandene Directorium `resources/directorium-2026-27-kern_21092026.pdf` enthält 377 liturgische Feiern für die 364 Kalendertage vom 29. November 2026 bis 27. November 2027. Gemeinsam gefeierte Heilige bleiben in einem Eintrag zusammen. Auch Sonntage, Herrenfeste und Marienfeiern sind enthalten.

| Verfügbarkeit | Anzahl | Bedeutung |
| --- | ---: | --- |
| `observed` | 154 | Im Tagesabschnitt angesetzte Feier |
| `optional` | 162 | Nichtgebotener Gedenktag |
| `commemoration_only` | 16 | Nur Kommemoration möglich |
| `suppressed` | 42 | In diesem Jahr entfallen bzw. verdrängt |
| `conditional` | 3 | Örtlich bedingt |

Am 25. Oktober gibt es zwei örtliche Varianten. Daher sind 365 Quellenabschnitte und 227 extrahierte PDF-Seiten hinterlegt.

## Tabellen

- `saints`: ID, Kalendertag, Datum, Kirchenjahr, Namen in beiden Sprachen, Kategorie, Rang, Kalenderkürzel, örtliche Bedingungen, liturgische Verfügbarkeit und `disabled`. Dazu kommen Quellenabschnitt, Quellenverweis, Originaltext und Änderungszeit. Es gibt keine Prüfstatus- oder Prüfnotizfelder.
- `calendar_days`: Datum, Kirchenjahr und Wochentag; liturgische Wochen werden später aus dem Kalender berechnet.
- `source_day_blocks`: datierte Originalabschnitte samt Varianten, Seitenspanne und Text. Lesungen, Farben und Rubriken bleiben im Originaltext erhalten.
- `source_pages`: vollständiger extrahierter Text jeder PDF-Seite.
- `import_runs`: Quelldateiname, SHA-256, Kirchenjahr, Diözese, Parser-Version, Importzeit, Bericht und Original-PDF als BLOB (`source_pdf`). Die API-Listen enthalten niemals die Binärdaten.

`name` und `name_sl` enthalten nur die Namen bzw. Festbezeichnungen. Angaben wie „Priester“, „Kirchenlehrer“ oder Kalenderverweise bleiben in `source_text`. Fehlende Übersetzungen bleiben `NULL`; es wird keine Übersetzung erfunden. Eigenständige Festnamen wie „Maria, Mutter der Kirche“ und identifizierende Zusätze wie „(Edith Stein)“ bleiben erhalten.

`disabled` ist ein Boolean, den SQLite als 0 oder 1 speichert. Die REST-API liefert `true` oder `false`. `rank_code` enthält `H`, `F`, `G`, `g` oder eine Kategorie wie `sunday`; fehlende Ränge bleiben `NULL`. Dies ist noch keine vollständige liturgische Vorrangberechnung.

`available_celebrations` liefert nicht deaktivierte Feiern mit Status `observed`, `optional` oder `commemoration_only`. Optionale Feiern bleiben Auswahlmöglichkeiten. Entfallene und örtlich bedingte Feiern werden nicht allein durch Aktivieren automatisch verfügbar.

## Upload und Import

Der Upload ist unter `POST /api/v1/imports/directorium` als Multipart-Feld `file` erreichbar. Die Oberfläche bietet denselben Vorgang über „Directorium hochladen“ an. Neue Directorien im Gurker Monats-/Tagesformat werden anhand der Textebene eingelesen. Jahr, Wochentage, Chronologie und die vollständige Abdeckung des Kirchenjahres werden geprüft. Seitenzahl und Position des Kalendariums sind nicht mehr fest vorgegeben. Nicht unterstützte Layouts werden abgelehnt.

Gleiche Prüfsummen führen zu einem bestehenden Import; Namen und Schalter bleiben unverändert. Pro Diözese und Kirchenjahr gibt es höchstens einen Import. Eine andere Ausgabe desselben Jahres ergibt einen Konflikt, ohne Daten zu überschreiben. Die Datei und alle Datensätze werden gemeinsam transaktional gespeichert. Der Quellenname wird auf den Dateinamen ohne Pfad reduziert. `GET /api/v1/imports/{id}/source` liefert das archivierte PDF.

Der bekannte Quelltext 2026/27 enthält widersprüchliche Jahresübersichten. Maßgeblich für diesen Import sind die datierten Tagesabschnitte. Bekannte editionsbezogene Sonderfälle werden weiterhin berücksichtigt. Originaltexte ermöglichen die Nachverfolgung; es gibt keinen manuellen Freigabeschritt.

## Migrationen und Sicherung

SQL-Migrationen liegen unter `verkuendigungen/infrastructure/migrations/`. Version 2 entfernt die ehemaligen Prüffelder und ergänzt das PDF-Archiv. IDs, Namen, Aktivierung und Originaltexte bleiben erhalten. Historische Migration 001 beschreibt weiterhin das damalige Schema; neue Datenbanken führen automatisch beide Migrationen aus.

Bei Altbeständen kann das Quellen-PDF durch erneuten Upload derselben Datei ergänzt werden, ohne die Einträge neu anzulegen. Zur Sicherung bei geschlossener Anwendung die vollständige SQLite-Datei kopieren. CSV und JSON-Bericht sind Exporte; die Datenbank bleibt maßgeblich. Tests verwenden separate Datenbanken.

## Kommandozeile

```powershell
python -m verkuendigungen init
python -m verkuendigungen import-directorium --source resources/directorium-2026-27-kern_21092026.pdf
python -m verkuendigungen status
python -m verkuendigungen list --start 2026-11-29 --end 2026-12-06 --all
python -m verkuendigungen disable 5
python -m verkuendigungen enable 5
python -m verkuendigungen export data/heilige-2026-27.csv
```

Ein anderer Datenbankpfad lässt sich vor dem Unterbefehl über `--db` angeben oder über `VERKUENDIGUNGEN_DB` konfigurieren.
