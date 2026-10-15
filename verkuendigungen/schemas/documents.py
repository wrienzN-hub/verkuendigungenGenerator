from datetime import date, timedelta
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

Text = Annotated[str, Field(max_length=10000)]
Identifier = Annotated[str, Field(min_length=1, max_length=100)]
Clock = Annotated[str, Field(pattern=r'^(?:[01]\d|2[0-3]):[0-5]\d$')]


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid')


class TextMark(Model):
    start: int = Field(ge=0)
    end: int = Field(ge=1)
    underline: StrictBool = False
    bold: StrictBool


class Bilingual(Model):
    de: Text = ''
    sl: Text = ''
    de_marks: list[TextMark] = Field(default_factory=list, max_length=500)
    sl_marks: list[TextMark] = Field(default_factory=list, max_length=500)

    @model_validator(mode='after')
    def valid_marks(self):
        for language in ['de', 'sl']:
            previous = 0
            for mark in getattr(self, language + '_marks'):
                if mark.start < previous or mark.end <= mark.start or mark.end > len(getattr(self, language)):
                    raise ValueError('Textformatierungen müssen zum Text passen und dürfen sich nicht überlappen.')
                previous = mark.end
        return self


class Visible(Model):
    id: Identifier
    enabled: StrictBool = True


class Celebration(Visible):
    source_celebration_id: int | None = None
    title: Bilingual
    rank: str | None = None


class Notice(Visible):
    text: Bilingual
    source_event_id: int | None = Field(default=None, ge=1)


class Intention(Notice):
    symbol: Annotated[str, Field(max_length=10)] = '+'
    reference: Annotated[str, Field(max_length=100)] | None = None


class Service(Visible):
    time: Clock | None = None
    location: Bilingual = Field(default_factory=Bilingual)
    title: Bilingual = Field(default_factory=Bilingual)
    intentions: list[Intention] = Field(default_factory=list, max_length=100)
    notices: list[Notice] = Field(default_factory=list, max_length=30)


    @model_validator(mode='after')
    def omit_service_title(self):
        self.title = Bilingual()
        return self


class Day(Visible):
    services_revision: int = Field(default=0, ge=0)
    date: date
    celebrations: list[Celebration] = Field(default_factory=list, max_length=30)
    services: list[Service] = Field(default_factory=list, max_length=30)
    notices: list[Notice] = Field(default_factory=list, max_length=30)


class Announcement(Visible):
    title: Bilingual = Field(default_factory=Bilingual)
    paragraphs: list[Bilingual] = Field(default_factory=list, max_length=30)


class Selection(Model):
    liturgical_year: str
    season: str
    week: int | None
    week_id: str


class Period(Model):
    start: date
    end: date


class Parish(Model):
    id: str
    name: Bilingual


class EternalLight(Model):
    enabled: StrictBool = True
    dedication: Bilingual = Field(default_factory=Bilingual)


class OfficeHours(Model):
    weekday: Annotated[str, Field(pattern='^(monday|tuesday|wednesday|thursday|friday|saturday|sunday)$')]
    from_: Clock = Field(alias='from')
    until: Clock

    @model_validator(mode='after')
    def valid_range(self):
        if self.from_ >= self.until:
            raise ValueError('Das Ende der Kanzleistunde muss nach dem Beginn liegen.')
        return self


class Person(Model):
    name: Annotated[str, Field(max_length=200)] = ''
    phone: Annotated[str, Field(max_length=100)] = ''


class Contact(Model):
    persons: list[Person] = Field(default_factory=list, max_length=20)
    email: Annotated[str, Field(max_length=200)] = ''
    website: Annotated[str, Field(max_length=300)] = ''


class DocumentPayload(Model):
    schema_version: int = Field(default=1, ge=1, le=1)
    template_id: int = Field(ge=0)
    template_version: str
    parish: Parish
    selection: Selection
    period: Period
    days: list[Day] = Field(min_length=8, max_length=8)
    announcements: list[Announcement] = Field(default_factory=list, max_length=50)
    eternal_light: EternalLight = Field(default_factory=EternalLight)
    office_hours: list[OfficeHours] = Field(default_factory=list, max_length=30)
    contact: Contact = Field(default_factory=Contact)

    @model_validator(mode='after')
    def valid_days(self):
        if self.period.end != self.period.start + timedelta(days=7) or self.period.start.weekday() != 6:
            raise ValueError('Der Zeitraum muss von Sonntag bis zum folgenden Sonntag reichen.')
        if [day.date for day in self.days] != [self.period.start + timedelta(days=i) for i in range(8)]:
            raise ValueError('Die Tage müssen vollständig und chronologisch zum Zeitraum passen.')
        ids = []
        for day in self.days:
            ids.append(day.id)
            ids.extend(item.id for item in [*day.celebrations, *day.notices])
            for service in day.services:
                ids.append(service.id)
                ids.extend(item.id for item in [*service.intentions, *service.notices])
        ids.extend(item.id for item in self.announcements)
        if len(ids) != len(set(ids)):
            raise ValueError('Alle Einträge benötigen eindeutige IDs.')
        if not self.parish.name.de.strip() and not self.parish.name.sl.strip():
            raise ValueError('Ein Pfarrname ist erforderlich.')
        return self


class PrepareDocument(Model):
    template_id: int = Field(ge=0)
    year: str = Field(max_length=20)
    week_id: str = Field(max_length=80)


class SaveDocument(Model):
    payload: DocumentPayload
    revision: int | None = Field(default=None, ge=1)


class RecurringService(Service):
    weekday: int = Field(ge=0, le=6)


class ParishDefaults(Model):
    services: list[RecurringService] = Field(default_factory=list, max_length=100)
    office_hours: list[OfficeHours] = Field(default_factory=list, max_length=30)
    contact: Contact = Field(default_factory=Contact)

    @model_validator(mode='after')
    def unique_services(self):
        ids = [service.id for service in self.services]
        if len(ids) != len(set(ids)):
            raise ValueError('Die Gottesdienste benötigen eindeutige IDs.')
        return self
