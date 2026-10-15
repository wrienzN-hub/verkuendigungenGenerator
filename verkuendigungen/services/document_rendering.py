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
from .rich_text import bilingual, bold_label, join_text

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
    marks = getattr(value, 'marks', [])
    boundaries = sorted({0, len(value), *(point for start, end, _, _ in marks for point in [start, end])})
    for start, end in zip(boundaries, boundaries[1:]):
        effective = next((weight for left, right, weight, _ in marks if left <= start and end <= right), bold)
        properties_copy = deepcopy(run_props)
        if effective is not None:
            for tag in ['b', 'bCs']:
                for item in properties_copy.findall('w:' + tag, NS):
                    properties_copy.remove(item)
                ET.SubElement(properties_copy, W + tag, {W + 'val': '1' if effective else '0'})
        underline = next((under for left, right, _, under in marks if left <= start and end <= right), False)
        for item in properties_copy.findall('w:u', NS):
            properties_copy.remove(item)
        ET.SubElement(properties_copy, W + 'u', {W + 'val': 'single' if underline else 'none'})
        run = ET.SubElement(result, W + 'r'); run.append(properties_copy)
        for index, line in enumerate(value[start:end].split('\n')):
            if index: ET.SubElement(run, W + 'br')
            for column, part in enumerate(line.split('\t')):
                if column: ET.SubElement(run, W + 'tab')
                node = ET.SubElement(run, W + 't', {'{http://www.w3.org/XML/1998/namespace}space': 'preserve'})
                node.text = part
    if not len(value):
        ET.SubElement(ET.SubElement(result, W + 'r'), W + 't').text = ''
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
                for intention in service.intentions:
                    if intention.enabled and bilingual(intention.text):
                        value = join_text([part for part in [intention.symbol, bilingual(intention.text), intention.reference] if part], ' ')
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


def office_lines(hours):
    groups = {}
    for item in hours:
        days = groups.setdefault((item.from_, item.until), [])
        if OFFICE_DAYS[item.weekday] not in days:
            days.append(OFFICE_DAYS[item.weekday])
    return [' & '.join(days) + f': {start}–{end} Uhr' for (start, end), days in groups.items()]


def contact_paragraph(prototype, value, body):
    result = paragraph(prototype, value, bold=False)
    if '\t' in value:
        section = body.find('w:sectPr', NS)
        size = section.find('w:pgSz', NS) if section is not None else None
        margins = section.find('w:pgMar', NS) if section is not None else None
        width = int(size.get(W + 'w', '11906')) if size is not None else 11906
        width -= int(margins.get(W + 'left', '540')) + int(margins.get(W + 'right', '851')) if margins is not None else 1391
        properties = result.find('w:pPr', NS)
        if properties is None:
            properties = ET.Element(W + 'pPr'); result.insert(0, properties)
        for tabs in properties.findall('w:tabs', NS):
            properties.remove(tabs)
        ET.SubElement(ET.SubElement(properties, W + 'tabs'), W + 'tab', {W + 'val': 'right', W + 'pos': str(width)})
    return result


def additional_lines(payload):
    lines = announcement_lines(payload)
    if payload.eternal_light.enabled and bilingual(payload.eternal_light.dedication):
        lines.append((bold_label('Das ewige Licht brennt für | Večna luč gori za:', bilingual(payload.eternal_light.dedication)), False))
    if payload.office_hours:
        lines.append(('Kanzleistunden | Uradne ure', True))
        lines.extend((value, False) for value in office_lines(payload.office_hours))
    lines.extend(contact_lines(payload))
    return lines


def normalize_overlaid_banner(body, table):
    """Repair the legacy Gurk pair of overlaid full-width banners only.

    A full-width image inside a floating text box is followed by another
    full-width picture in the same paragraph. This is already broken in the
    source. Keep the first branding image as an inline banner, removing the
    overlay and the stray positioning text. Other templates are untouched.
    """
    v = {'v': 'urn:schemas-microsoft-com:vml', **NS}
    prefix = list(body)[:list(body).index(table)]
    for node in prefix:
        nested = node.xpath('.//w:txbxContent//w:pict[v:shape/v:imagedata]', namespaces=v)
        peers = node.xpath('./w:r/w:pict[v:shape/v:imagedata]', namespaces=v) or nested[1:]
        if not nested or not peers:
            continue
        shape = nested[0].find('v:shape', v)
        peer_shape = peers[0].find('v:shape', v)
        def size(item):
            values = dict(part.strip().split(':', 1) for part in item.get('style', '').split(';') if ':' in part)
            try:
                return float(values['width'].removesuffix('pt')), float(values['height'].removesuffix('pt'))
            except (ValueError, KeyError):
                return 0, 0
        width, height = size(shape)
        if width < 500 or size(peer_shape)[0] < 500:
            continue
        heading = next((p for p in prefix if p.tag == W + 'p' and 'Heilige Messen' in plain(p)), None)
        if heading is None:
            continue
        picture = deepcopy(nested[0])
        cloned_shape = picture.find('v:shape', v)
        table_width = table.find('w:tblPr/w:tblW', NS)
        target_width = float(table_width.get(W + 'w', '11100')) / 20 if table_width is not None else 555
        cloned_shape.set('style', f'width:{target_width:g}pt;height:{height * target_width / width:g}pt')
        banner = ET.Element(W + 'p')
        props = ET.SubElement(banner, W + 'pPr')
        ET.SubElement(props, W + 'spacing', {W + 'after': '160'})
        ET.SubElement(props, W + 'ind', {W + 'left': '-115'})
        ET.SubElement(banner, W + 'r').append(picture)
        for old in prefix:
            body.remove(old)
        body.insert(0, banner)
        body.insert(1, heading)
        body.insert(2, ET.Element(W + 'p'))
        return True
    return False


def render_docx(source: bytes, payload: DocumentPayload):
    with ZipFile(BytesIO(source)) as archive:
        root = xml_root(archive.read('word/document.xml'))
        body = root.find('w:body', NS)
        table = table_slot(root)
        extra = additional_lines(payload)
        if table is not None:
            normalize_overlaid_banner(body, table)
            day_rows(table, payload)
            # The Gurk template's variable area starts after the schedule. Keep
            # its logo, title, table grid, sections, styles and package parts.
            siblings = list(body)
            tail = siblings[siblings.index(table) + 1:]
            heading = next((node for node in tail if node.tag == W + 'p' and 'Termine' in plain(node)), None)
            prototype = next((node for node in tail if node.tag == W + 'p' and plain(node) and node is not heading), ET.Element(W + 'p'))
            footer = next((node for node in tail if node.tag == W + 'tbl' and ('ewige Licht' in plain(node) or 'Kanzlei' in plain(node))), None)
            contact_prototypes = [node for node in tail if node.tag == W + 'p' and plain(node) and node is not heading]
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
                if (announcements or (payload.eternal_light.enabled and bilingual(payload.eternal_light.dedication))) and heading is not None:
                    append(paragraph(heading, 'Termine | Termini'))
                # Retain the template's bordered eternal-light/office-hours box.
                footer_rows = footer.findall('w:tr', NS)
                for index, row in enumerate(footer_rows):
                    values = []
                    label = plain(row).casefold()
                    if 'ewige licht' in label and payload.eternal_light.enabled and bilingual(payload.eternal_light.dedication):
                        values = [(bold_label('Das ewige Licht brennt für | Večna luč gori za:', bilingual(payload.eternal_light.dedication)), False)]
                    elif 'kanzlei' in label and payload.office_hours:
                        values = [('Kanzleistunden | Uradne ure', True)] + [(hours, False) for hours in office_lines(payload.office_hours)]
                    if not values:
                        footer.remove(row)
                        continue
                    for height in row.findall('w:trPr/w:trHeight', NS) + row.findall('w:trPr/w:cantSplit', NS):
                        height.getparent().remove(height)
                    cells = row.findall('w:tc', NS)
                    fill_cell(cells[0], values)
                    if 'kanzlei' in label:
                        for p in cells[0].findall('w:p', NS):
                            props = p.find('w:pPr', NS)
                            if props is None:
                                props = ET.Element(W + 'pPr'); p.insert(0, props)
                            for node in props.findall('w:jc', NS) + props.findall('w:spacing', NS):
                                props.remove(node)
                            ET.SubElement(props, W + 'jc', {W + 'val': 'left'})
                            ET.SubElement(props, W + 'spacing', {W + 'before': '0', W + 'after': '40'})
                    for cell in cells[1:]:
                        fill_cell(cell, [])
                # One framed row per free-form announcement, between the light
                # dedication and office hours, using the source table's geometry.
                announcement_prototype = deepcopy(footer_rows[0])
                office_row = next((row for row in footer.findall('w:tr', NS) if 'Kanzleistunden' in plain(row)), None)
                for announcement in payload.announcements:
                    if not announcement.enabled:
                        continue
                    lines = []
                    if bilingual(announcement.title):
                        lines.append((bilingual(announcement.title), True))
                    lines.extend((bilingual(part), False) for part in announcement.paragraphs if bilingual(part))
                    if not lines:
                        continue
                    row = deepcopy(announcement_prototype)
                    for child in row.findall('w:trPr/w:trHeight', NS) + row.findall('w:trPr/w:cantSplit', NS):
                        child.getparent().remove(child)
                    cells = row.findall('w:tc', NS)
                    fill_cell(cells[0], lines)
                    for cell in cells[1:]:
                        fill_cell(cell, [])
                    if office_row is not None:
                        office_row.addprevious(row)
                    else:
                        footer.append(row)
                if footer.findall('w:tr', NS):
                    append(paragraph(prototype, ''))
                    append(footer)
                if contact_lines(payload):
                    append(paragraph(prototype, ''))
                    persons = [' · '.join(part for part in [p.name, p.phone] if part) for p in payload.contact.persons if p.name or p.phone]
                    for index in range(0, len(persons), 2):
                        append(contact_paragraph(prototype, '\t'.join(persons[index:index+2]), body))
                    links = [value for value in [('E-Mail: ' + payload.contact.email) if payload.contact.email else '', payload.contact.website] if value]
                    if links:
                        link_prototype = contact_prototypes[1] if len(contact_prototypes) > 1 else prototype
                        append(contact_paragraph(link_prototype, '\t'.join(links), body))
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
                        content.append((' · '.join(p for p in [service.time, bilingual(service.location)] if p), False))
                        content.extend((join_text([p for p in [i.symbol, bilingual(i.text), i.reference] if p], ' '), False) for i in service.intentions if i.enabled and bilingual(i.text))
                        content.extend(notice_lines(service.notices))
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
