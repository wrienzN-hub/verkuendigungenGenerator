"""Kleine synthetische Directorien für Upload- und Kalenderprüfungen."""
from collections import defaultdict
from io import BytesIO

from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

from verkuendigungen.services.directorium import first_advent, WEEKDAYS
from datetime import timedelta


def directorium_pdf(year=2027, *, omit=None, wrong_weekday=False, encrypted=False):
    months = ['JANUAR','FEBRUAR','MÄRZ','APRIL','MAI','JUNI','JULI','AUGUST','SEPTEMBER','OKTOBER','NOVEMBER','DEZEMBER']
    writer = PdfWriter()
    def page(lines):
        p = writer.add_blank_page(width=595,height=842)
        p[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica'),NameObject('/Encoding'):NameObject('/WinAnsiEncoding')})})})
        escaped = [''.join(f'\\{byte:03o}' for byte in line.encode('cp1252')) for line in lines]
        content = 'BT /F1 7 Tf 7 TL 30 810 Td\n' + '\n'.join(f'({line}) Tj T*' for line in escaped) + '\nET'
        stream=DecodedStreamObject();stream.set_data(content.encode('ascii'))
        p[NameObject('/Contents')] = writer._add_object(stream)
    page(['Directorium Diözese Gurk',f'Kirchenjahr {year}/{year+1}'])
    grouped=defaultdict(list)
    current=first_advent(year);end=first_advent(year+1)
    while current<end:
        if current.isoformat()!=omit:
            grouped[(current.year,current.month)].append(current)
        current+=timedelta(days=1)
    for (calendar_year,month),days in grouped.items():
        lines=[f'{months[month-1]} {calendar_year}']
        for index,day in enumerate(days):
            weekday=WEEKDAYS[day.weekday()]
            if wrong_weekday and month==1 and index==0:
                weekday=WEEKDAYS[(day.weekday()+1)%7]
            lines.append(f'{day.day} {weekday} '+('+ SONNTAG' if day.weekday()==6 else 'der Woche im Jahreskreis'))
            if day.weekday()!=6:
                lines.append('g Hl. Beispiel, Priester, Kirchenlehrer')
            lines.append('Off vom So' if day.weekday()==6 else 'Off vom Tag oder vom g')
        page(lines)
    if encrypted:writer.encrypt('secret')
    result=BytesIO();writer.write(result);return result.getvalue()
