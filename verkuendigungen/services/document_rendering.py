"""Fill existing OOXML components; preserve all other ZIP members byte for byte."""

from copy import deepcopy
from io import BytesIO
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
from zipfile import ZipFile

from lxml import etree as ET

from ..schemas.documents import DocumentPayload

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
W = '{' + NS['w'] + '}'
DAYS = ['Montag | ponedeljek', 'Dienstag | torek', 'Mittwoch | sreda', 'Donnerstag | četrtek', 'Freitag | petek', 'Samstag | sobota', 'Sonntag | nedelja']
OFFICE_DAYS = dict(zip(['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'], DAYS))
CONVERSION_LOCK = threading.Lock()


class ConversionError(Exception):
    pass


def xml_root(data):
    return ET.fromstring(data, parser=ET.XMLParser(resolve_entities=False, no_network=True))


def text(node):
    return ''.join(node.itertext()) if node is not None else ''


def plain(node):
    return ''.join(node.xpath('.//w:t/text()', namespaces=NS))


def table_slot(root):
    for table in root.findall('.//w:body/w:tbl', NS):
        rows = table.findall('w:tr', NS)
        if rows and len(rows[0].findall('w:tc', NS)) == 4 and any(day in plain(table).lower() for day in ['sonntag', 'nedelja']):
            return table
    return None


def template_supported(data):
    with ZipFile(BytesIO(data)) as archive:
        root = xml_root(archive.read('word/document.xml'))
        marker = any(plain(p).strip() == '{{inhalt}}' for p in root.findall('.//w:body/w:p', NS))
        return table_slot(root) is not None or marker


def bilingual(value):
    return ' | '.join(part.strip() for part in [value.de, value.sl] if part.strip())


def paragraph(prototype, value, *, bold=None):
    result = deepcopy(prototype)
    properties = result.find('w:pPr', NS)
    run_props = result.find('w:r/w:rPr', NS)
    if run_props is None:
        run_props = result.find('w:pPr/w:rPr', NS)
    run_props = deepcopy(run_props) if run_props is not None else ET.Element(W + 'rPr')
    for child in list(result):
        if child is not properties:
            result.remove(child)
    if properties is not None:
        for tag in ['sectPr', 'pageBreakBefore', 'keepNext']:
            for item in properties.findall('w:' + tag, NS):
                properties.remove(item)
    if bold is not None:
        for item in run_props.findall('w:b', NS):
            run_props.remove(item)
        ET.SubElement(run_props, W + 'b', {W + 'val': '1' if bold else '0'})
    run = ET.SubElement(result, W + 'r')
    run.append(run_props)
    for index, line in enumerate(value.split('\n')):
        if index:
            ET.SubElement(run, W + 'br')
        node = ET.SubElement(run, W + 't', {'{http://www.w3.org/XML/1998/namespace}space': 'preserve'})
        node.text = line
    return result


def fill_cell(cell, lines):
    prototype = cell.find('w:p', NS)
    if prototype is None:
        prototype = ET.Element(W + 'p')
    for child in list(cell):
        if child.tag != W + 'tcPr':
            cell.remove(child)
    for value, bold in lines or [('', False)]:
        cell.append(paragraph(prototype, value, bold=bold))
    # Cloned source rows must not retain vertical merges or exact fixed heights.
    for merge in cell.findall('w:tcPr/w:vMerge', NS):
        merge.getparent().remove(merge)


def notice_lines(notices):
    return [(bilingual(item.text), False) for item in notices if item.enabled and bilingual(item.text)]


def day_rows(table, payload):
    prototype = deepcopy(table.find('w:tr', NS))
    for row in table.findall('w:tr', NS):
        table.remove(row)
    count = 0
    for day in payload.days:
        if not day.enabled:
            continue
        celebrations = [(bilingual(item.title), True) for item in day.celebrations if item.enabled and bilingual(item.title)]
        notices = notice_lines(day.notices)
        services = [service for service in day.services if service.enabled]
        if not celebrations and not notices and not services:
            continue
        for index, service in enumerate(services or [None]):
            row = deepcopy(prototype)
            for height in row.findall('w:trPr/w:trHeight', NS):
                height.getparent().remove(height)
            # Allow a long intentions list to continue on the next page.
            for item in row.findall('w:trPr/w:cantSplit', NS):
                item.getparent().remove(item)
            cells = row.findall('w:tc', NS)
            fill_cell(cells[0], [(DAYS[day.date.weekday()], False), (day.date.strftime('%d.%m.%Y'), True)] if index == 0 else [])
            fill_cell(cells[1], [(service.time or '', True)] if service else [])
            fill_cell(cells[2], [(bilingual(service.location), False)] if service else [])
            lines = celebrations + notices if index == 0 else []
            if service:
                if bilingual(service.title):
                    lines.append((bilingual(service.title), False))
                for intention in service.intentions:
                    if intention.enabled and bilingual(intention.text):
                        value = ' '.join(part for part in [intention.symbol, bilingual(intention.text), intention.reference] if part)
                        lines.append((value, False))
                lines.extend(notice_lines(service.notices))
            fill_cell(cells[3], lines)
            table.append(row)
            count += 1
    return count


def announcement_lines(payload):
    lines = []
    for item in payload.announcements:
        if item.enabled:
            if bilingual(item.title):
                lines.append((bilingual(item.title), True))
            lines.extend((bilingual(p), False) for p in item.paragraphs if bilingual(p))
    return lines


def contact_lines(payload):
    lines = [(' · '.join(part for part in [person.name, person.phone] if part), False) for person in payload.contact.persons if person.name or person.phone]
    lines.extend((value, False) for value in [payload.contact.email, payload.contact.website] if value)
    return lines


def additional_lines(payload):
    lines = announcement_lines(payload)
    if payload.eternal_light.enabled and bilingual(payload.eternal_light.dedication):
        lines.append(('Das ewige Licht brennt für | Večna luč gori za: ' + bilingual(payload.eternal_light.dedication), False))
    if payload.office_hours:
        lines.append(('Kanzleistunden | Uradne ure', True))
        lines.extend((f'{OFFICE_DAYS[item.weekday]}: {item.from_}–{item.until}', False) for item in payload.office_hours)
    lines.extend(contact_lines(payload))
    return lines


def render_docx(source: bytes, payload: DocumentPayload):
    with ZipFile(BytesIO(source)) as archive:
        root = xml_root(archive.read('word/document.xml'))
        body = root.find('w:body', NS)
        table = table_slot(root)
        extra = additional_lines(payload)
        if table is not None:
            day_rows(table, payload)
            # The Gurk template's variable area starts after the schedule. Keep
            # its logo, title, table grid, sections, styles and package parts.
            siblings = list(body)
            tail = siblings[siblings.index(table) + 1:]
            heading = next((node for node in tail if node.tag == W + 'p' and 'Termine' in plain(node)), None)
            prototype = next((node for node in tail if node.tag == W + 'p' and plain(node) and node is not heading), ET.Element(W + 'p'))
            footer = next((node for node in tail if node.tag == W + 'tbl' and 'ewige Licht' in plain(node) and 'Kanzlei' in plain(node)), None)
            section = body.find('w:sectPr', NS)
            for node in tail:
                if node is not section:
                    body.remove(node)
            def append(node):
                body.insert(list(body).index(section) if section is not None else len(body), node)
            if footer is None:
                if extra and heading is not None:
                    append(paragraph(heading, 'Termine und Hinweise | Termini in obvestila'))
                for value, bold in extra:
                    append(paragraph(prototype, value, bold=bold))
            else:
                announcements = announcement_lines(payload)
                if announcements:
                    if heading is not None:
                        append(paragraph(heading, 'Termine | Termini'))
                    for value, bold in announcements:
                        append(paragraph(prototype, value, bold=bold))
                # Retain the template's bordered eternal-light/office-hours box.
                footer_rows = footer.findall('w:tr', NS)
                for index, row in enumerate(footer_rows):
                    values = []
                    if index == 0 and payload.eternal_light.enabled and bilingual(payload.eternal_light.dedication):
                        values = [('Das ewige Licht brennt für | Večna luč gori za: ' + bilingual(payload.eternal_light.dedication), True)]
                    elif index == 1 and payload.office_hours:
                        values = [('Kanzleistunden | Uradne ure', True)] + [(f'{OFFICE_DAYS[h.weekday]}: {h.from_}–{h.until}', False) for h in payload.office_hours]
                    if not values:
                        footer.remove(row)
                        continue
                    for height in row.findall('w:trPr/w:trHeight', NS) + row.findall('w:trPr/w:cantSplit', NS):
                        height.getparent().remove(height)
                    cells = row.findall('w:tc', NS)
                    fill_cell(cells[0], values)
                    for cell in cells[1:]:
                        fill_cell(cell, [])
                if footer.findall('w:tr', NS):
                    append(paragraph(prototype, ''))
                    append(footer)
                if contact_lines(payload):
                    append(paragraph(prototype, ''))
                    for value, bold in contact_lines(payload):
                        append(paragraph(prototype, value, bold=bold))
        else:
            marker = next((p for p in body.findall('w:p', NS) if plain(p).strip() == '{{inhalt}}'), None)
            if marker is None:
                raise ValueError('Diese Vorlage hat keine unterstützte Wochentabelle. Verwende die vorhandene Eberndorfer Vorlage oder einen eigenen Absatz mit {{inhalt}}.')
            lines = [(bilingual(payload.parish.name), True), (f'{payload.period.start:%d.%m.%Y}–{payload.period.end:%d.%m.%Y}', False)]
            for day in payload.days:
                if not day.enabled:
                    continue
                content = [(bilingual(c.title), True) for c in day.celebrations if c.enabled and bilingual(c.title)] + notice_lines(day.notices)
                for service in day.services:
                    if service.enabled:
                        content.append((' · '.join(p for p in [service.time, bilingual(service.location), bilingual(service.title)] if p), False))
                        content.extend((' '.join(p for p in [i.symbol, bilingual(i.text), i.reference] if p), False) for i in service.intentions if i.enabled and bilingual(i.text))
                        content.extend(notice_lines(service.notices))
                if content:
                    lines.append((f'{DAYS[day.date.weekday()]} {day.date:%d.%m.%Y}', True))
                    lines.extend(content)
            for value, bold in lines + extra:
                marker.addprevious(paragraph(marker, value, bold=bold))
            body.remove(marker)
        # Simple metadata placeholders may span several Word runs.
        replacements = {'{{pfarre}}': bilingual(payload.parish.name), '{{von}}': payload.period.start.strftime('%d.%m.%Y'), '{{bis}}': payload.period.end.strftime('%d.%m.%Y')}
        for p in root.findall('.//w:p', NS):
            original = plain(p)
            replaced = original
            for key, value in replacements.items():
                replaced = replaced.replace(key, value)
            if replaced != original:
                p.getparent().replace(p, paragraph(p, replaced))
        output = BytesIO()
        with ZipFile(output, 'w') as target:
            for entry in archive.infolist():
                data = ET.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True) if entry.filename == 'word/document.xml' else archive.read(entry.filename)
                target.writestr(entry, data)
        return output.getvalue()


def libreoffice_path():
    explicit = os.environ.get('VERKUENDIGUNGEN_SOFFICE')
    if explicit:
        return explicit if Path(explicit).is_file() else None
    return shutil.which('soffice') or shutil.which('soffice.exe') or next((str(p) for p in [Path('C:/Program Files/LibreOffice/program/soffice.exe'), Path('/Applications/LibreOffice.app/Contents/MacOS/soffice')] if p.is_file()), None)


def converter_available():
    if libreoffice_path():
        return True
    if sys.platform == 'win32':
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r'Word.Application\CLSID'):
                return True
        except OSError:
            pass
    return False


def convert_pdf(docx: bytes):
    if not CONVERSION_LOCK.acquire(timeout=10):
        raise ConversionError('Eine andere PDF-Erstellung läuft gerade. Bitte gleich erneut versuchen.')
    try:
        with tempfile.TemporaryDirectory(prefix='verkuendigungen-') as folder:
            directory = Path(folder)
            source, target = directory / 'abkuendigung.docx', directory / 'abkuendigung.pdf'
            source.write_bytes(docx)
            soffice = libreoffice_path()
            if soffice:
                command = [soffice, '-env:UserInstallation=' + (directory / 'profile').as_uri(), '--headless', '--convert-to', 'pdf', '--outdir', str(directory), str(source)]
            elif sys.platform == 'win32':
                command = ['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(Path(__file__).with_name('word_to_pdf.ps1')), '-InputFile', str(source), '-OutputFile', str(target)]
            else:
                raise ConversionError('Für die PDF-Erstellung wird LibreOffice benötigt. Bitte LibreOffice installieren und den Server neu starten.')
            try:
                result = subprocess.run(command, capture_output=True, timeout=90, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise ConversionError('Die PDF-Konvertierung konnte nicht abgeschlossen werden. Bitte Word bzw. LibreOffice und den Serverstart prüfen.') from exc
            if result.returncode or not target.is_file():
                raise ConversionError('Die PDF-Konvertierung ist fehlgeschlagen. Microsoft Word muss für diesen Windows-Benutzer eingerichtet sein; alternativ LibreOffice installieren. Der Entwurf bleibt gespeichert.')
            data = target.read_bytes()
            if not data.startswith(b'%PDF-'):
                raise ConversionError('Die Konvertierung hat keine gültige PDF-Datei erzeugt.')
            return data
    finally:
        CONVERSION_LOCK.release()
