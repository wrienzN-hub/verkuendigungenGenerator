"""Validate Word templates without executing or changing their contents."""

from io import BytesIO
from zipfile import BadZipFile, ZipFile
from xml.etree import ElementTree as ET


def validate_docx(data: bytes):
    try:
        with ZipFile(BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > 2000 or sum(item.file_size for item in entries) > 100 * 1024 * 1024:
                raise ValueError('Die entpackte Word-Datei ist zu groß.')
            if any(item.flag_bits & 1 for item in entries):
                raise ValueError('Passwortgeschützte Word-Dateien werden nicht unterstützt.')
            content_types = ET.fromstring(archive.read('[Content_Types].xml'))
            main_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml'
            if not any(item.get('PartName') == '/word/document.xml' and item.get('ContentType') == main_type for item in content_types):
                raise ValueError('Bitte eine Word-Vorlage im DOCX-Format ohne Makros auswählen.')
            if any('macro' in item.get('ContentType', '').lower() for item in content_types):
                raise ValueError('Word-Dateien mit Makros werden nicht unterstützt.')
            root = ET.fromstring(archive.read('word/document.xml'))
            ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
            if root.tag != ns + 'document' or root.find(ns + 'body') is None:
                raise ValueError('Die Datei enthält kein lesbares Word-Dokument.')
    except (BadZipFile, KeyError, ET.ParseError, RuntimeError, NotImplementedError, EOFError) as exc:
        raise ValueError('Die Datei ist keine gültige, lesbare DOCX-Datei.') from exc
