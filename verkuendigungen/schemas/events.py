from typing import Annotated
from pydantic import Field, model_validator
from .documents import Bilingual, Model

class EventWeek(Model):
    year: Annotated[str, Field(pattern=r'^20\d{2}/\d{2}$')]
    week_id: Annotated[str, Field(min_length=1, max_length=100)]

class EventInput(Model):
    name: Annotated[str, Field(min_length=1, max_length=200)]
    parishes: list[Annotated[str, Field(min_length=1, max_length=120)]] = Field(min_length=1, max_length=100)
    weeks: list[EventWeek] = Field(default_factory=list, max_length=500)
    text: Bilingual

    @model_validator(mode='after')
    def content_required(self):
        self.name = self.name.strip()
        self.parishes = list(dict.fromkeys(p.strip() for p in self.parishes))
        if not self.name or any(not p for p in self.parishes) or not (self.text.de.strip() or self.text.sl.strip()):
            raise ValueError('Name, Pfarre und Inhalt sind erforderlich.')
        if len({(w.year,w.week_id) for w in self.weeks}) != len(self.weeks):
            raise ValueError('Wochen duerfen nicht doppelt vorkommen.')
        return self

class EventUpdate(EventInput):
    revision: int = Field(ge=1)
