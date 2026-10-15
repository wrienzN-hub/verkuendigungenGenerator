# Verkündigungen erstellen

## Implementierter Stand

Die Erstellung ist unter **Erstellen** verfügbar. Auswahl, acht bearbeitbare Tage, zweisprachige Gottesdienste mit mehreren Intentionen, Hinweise, Ankündigungen mit Absätzen, Ewiges Licht, Kanzleistunden, Kontakte, gespeicherte Entwürfe und PDF-Download sind umgesetzt. Die Generatorauswahl verwendet das tatsächliche importierte Kirchenjahr mit dem ersten Adventssonntag; der Dezember-bis-November-Filter der Heiligenverwaltung bleibt davon unabhängig.

Das verbindliche Schema liegt in `verkuendigungen/schemas/documents.py`. `template_id` ist eine numerische Vorlagen-ID; ID 0 steht für die eingebaute Eberndorfer Vorlage. `template_version` ist der SHA-256 der Originaldatei. `selection.week_id` hält zusätzlich die eindeutige Wochenkennung fest. Die ursprüngliche JSON-Strukturvorlage unten dient weiterhin als Beispiel und enthält nur einen exemplarischen Tag.

`document_payloads` speichert das gesamte JSON und die Originalvorlage als Momentaufnahme. Die Revision verhindert unbeabsichtigtes Überschreiben durch parallele Bearbeitung. Jede Änderung entfernt die bisherige Ausgabe. DOCX und PDF werden aus demselben gespeicherten Stand erzeugt und nur angehängt, wenn sich dessen Revision währenddessen nicht geändert hat.

Der Renderer unterstützt die vorhandene vierteilige Wochentabelle. Logo, Titel, Seitengeometrie und alle unveränderten ZIP-Bestandteile bleiben erhalten. Tageszeilen werden aus den Tabellenzellen der Vorlage abgeleitet; Termine, Ewiges Licht, Kanzleistunden und Kontakt werden mit den aktuellen Angaben befüllt. Eigene Vorlagen können alternativ einen separaten Absatz `{{inhalt}}` für die gesamten dynamischen Inhalte verwenden; optionale Textmarker im Dokumentkörper sind `{{pfarre}}`, `{{von}}` und `{{bis}}`. Beliebige Word-Dateien ohne eine dieser Strukturen können gespeichert, aber nicht automatisch zugeordnet werden; die Auswahl kennzeichnet sie entsprechend.

Die PDF-Konvertierung verwendet LibreOffice, sofern gefunden, ansonsten unter Windows Microsoft Word im Hintergrund. Bei fehlgeschlagener Konvertierung bleibt der Entwurf gespeichert. Für den Betrieb in einem Linux-Container muss LibreOffice installiert werden. Für den lokalen Windows-Betrieb mit Word ist kein Container erforderlich.

Die Anwendung erstellt zweisprachige Verkündigungen für die Diözese Gurk. Mitarbeitende wählen ein Kirchenjahr, eine liturgische Zeit und deren Woche, beispielsweise „2026/27 → Advent → 1. Woche“. Die Anwendung berechnet daraus den Zeitraum vom ersten bis einschließlich des folgenden Sonntags. Das gewünschte Endprodukt ist ein PDF auf Grundlage der austauschbaren Word-Vorlage.

## Ablauf

1. Kirchenjahr, liturgische Zeit und Woche auswählen. Die Oberfläche bietet nur gültige Kombinationen an. Liturgische Zeiten erhalten eindeutige Werte, etwa `advent`, `christmas`, `lent`, `easter` und `ordinary_time`. Bei besonderen Wochen muss die spätere Kalenderlogik eine eindeutige Auswahl anbieten.
2. Den Zeitraum anhand des liturgischen Kalenders berechnen. Keine Ableitung aus ISO-Kalenderwochen oder einem festen Beginn am 1. Dezember verwenden.
3. Die gültigen Sonntage, Feste, Heiligen und Gedenktage aus der Datenbank laden. Deaktivierte Einträge und die liturgische Rangordnung berücksichtigen. Alle acht Tage des Zeitraums zunächst bereitstellen.
4. Das vollständige JSON in die Bearbeitungsoberfläche laden. Mitarbeitende können Texte ändern, Tage ausblenden sowie Gottesdienste, Orte, Uhrzeiten, Messintentionen, Hinweise und Termine ergänzen.
5. Den bearbeiteten Inhalt als Ganzes in `document_payloads.payload_json` speichern. Eine erneute Datenübernahme darf manuelle Änderungen nicht unbemerkt überschreiben. Eine Änderung der Wochenauswahl erzeugt einen neuen Entwurf oder benötigt eine ausdrückliche Übernahme in den bestehenden Entwurf.
6. Das gespeicherte JSON prüfen, die Word-Vorlage füllen und das resultierende Dokument nach PDF konvertieren. Das PDF zum Download anbieten. DOCX ist das interne Zwischenformat; ein zusätzlicher Word-Download kann später ergänzt werden.

## JSON-Vertrag

Das Template liegt unter `resources/templates/document-payload.template.json`. Es ist gültiges JSON als Strukturvorlage, noch kein JSON Schema und kein vollständig ausgefülltes Dokument. Es enthält exemplarisch nur den ersten Tag der ersten Adventswoche 2026/27. Beim Laden ergänzt die Anwendung alle acht Tage bis zum 6. Dezember. Leere Beispielobjekte für Intentionen, Hinweise und Termine werden im tatsächlichen Entwurf durch leere Listen ersetzt, solange keine Inhalte vorhanden sind. Die Kanzleistunden sind Beispielwerte aus der ausgefüllten Verkündigung und keine verbindlichen Standardwerte.

- `schema_version` bezeichnet die Datenstruktur; `template_id` und `template_version` wählen die passende Word-Vorlage.
- `selection` hält die Auswahl fest. `period` wird daraus berechnet und darf nicht unabhängig davon geändert werden. Eine technische Kalenderwoche ist nicht erforderlich.
- `days` enthält die Tage in chronologischer Reihenfolge. `enabled: false` blendet einen Tag samt Inhalten aus. Tage ohne Messe können trotzdem einen Gedenktag oder Hinweis enthalten.
- `celebrations` enthält die an diesem Datum gültigen Sonntage, Feste und Heiligen. `source_celebration_id` verweist bei importierten Einträgen auf den Datenbankdatensatz; bei manuell erfassten Einträgen ist der Wert `null`. `rank` wird aus dem Kalender übernommen und dient der fachlichen Zuordnung, nicht der freien Textformatierung.
- `services` erlaubt mehrere Gottesdienste pro Tag mit jeweils eigener Uhrzeit, eigenem Ort, Titel, mehreren Intentionen und Hinweisen. Die Reihenfolge der Listen bestimmt die Ausgabe.
- `intentions[].reference` ist eine optionale Zeichenfolge für Angaben wie `614/25` oder `30. Tag / dan`; diese Angaben nicht als Zahl speichern. Das Kreuzzeichen wird separat unter `symbol` geführt.
- `notices` am Tag ermöglicht etwa „Keine hl. Messe“. Hinweise am Gottesdienst ermöglichen etwa Erntedank, eine Kollekte oder eine Aktion nach der Messe. Beide verwenden dieselbe Struktur aus `id`, `enabled` und zweisprachigem `text`.
- `announcements` enthält frei bearbeitbare Termine mit Überschrift und mehreren Absätzen. Damit lassen sich auch Anmeldung, Preis und Kontakthinweise einer Wallfahrt abbilden.
- `eternal_light`, `office_hours` und `contact` enthalten die weiteren Bereiche der Vorlage.
- Zweisprachige Texte stehen als `{ "de": "...", "sl": "..." }` zusammen. Eine Sprache darf leer bleiben; der Renderer gibt vorhandene Texte aus und erzeugt keine automatische Übersetzung. Namen oder bereits gemischte Texte können einmalig in einem Sprachfeld stehen.
- Stabile IDs ermöglichen der Oberfläche, einzelne Einträge gezielt zu bearbeiten. Sie sind keine sichtbaren Dokumentnummern.

## Speicherung und Ausgabe

Das JSON enthält eine vollständige Momentaufnahme einschließlich Texten und Kontaktdaten. Eine spätere Änderung an Heiligen oder Pfarrstammdaten verändert damit keine gespeicherte Verkündigung. IDs, Erstellungszeit und Bearbeitungszeit des Dokuments können als Spalten neben `payload_json` gespeichert werden.

Datumsformat und Wochentagsnamen entstehen aus dem ISO-Datum. Schrift, Tabellenbreiten, feste Beschriftungen und die Anordnung der Sprachen bleiben in der Word-Vorlage. Leere Texte und deaktivierte Einträge werden nicht gedruckt. Eine fehlende Uhrzeit wird als leere Zelle dargestellt; ein Gottesdienst muss keine Uhrzeit haben, solange er noch im Entwurf ist.

Vor der PDF-Ausgabe werden Datumsbereich, eindeutige IDs, gültige Uhrzeiten und mindestens ein sichtbarer Inhalt geprüft. Die Dokumenterzeugung muss Tabellen mit mehreren Intentionen und langen Terminen über Seitengrenzen hinweg sauber darstellen. Das ausgefüllte Beispiel zeigt zudem, dass Tage ohne relevante Inhalte ausgelassen werden können; eine automatische Ausblendung solcher Tage ist zusätzlich zu den manuellen Schaltern sinnvoll.

Dieser Ablauf konkretisiert die bisherige README: Das Ausgabeziel ist PDF, und die Auswahl erfolgt über die liturgische Woche. Der Directorium-Import und die Verwaltung der Heiligen bleiben die Grundlage dafür.
