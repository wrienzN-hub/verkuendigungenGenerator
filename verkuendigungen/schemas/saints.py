from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, StrictBool, Field, model_validator

Rank = Literal['H','F','G','g','sunday','privileged_weekday','triduum','octave','commemoration']
Observance = Literal['observed','optional','commemoration_only','suppressed','conditional']


class SaintUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    disabled: StrictBool | None = None
    name: str | None = Field(default=None,min_length=1,max_length=500)
    name_sl: str | None = Field(default=None,max_length=500)
    rank_code: Rank | None = None
    observance_status: Observance | None = None
    applicability_note: str | None = Field(default=None,max_length=5000)

    @model_validator(mode='after')
    def validate_patch(self):
        if not self.model_fields_set:
            raise ValueError('Mindestens ein Feld ist erforderlich.')
        for field in self.model_fields_set - {'name_sl','rank_code','applicability_note'}:
            if getattr(self,field) is None:
                raise ValueError(f'{field} darf nicht null sein.')
        return self


class Saint(BaseModel):
    id: int
    calendar_day_id: int
    source_block_id: int
    liturgical_year: str
    celebration_date: date
    name: str
    name_sl: str | None
    kind: str
    rank_code: str | None
    calendar_scope: str
    applicability_note: str | None
    observance_status: Literal['observed', 'optional', 'commemoration_only', 'suppressed', 'conditional']
    disabled: bool
    source_page: int
    source_reference: str
    source_text: str
    updated_at: datetime


class SaintPage(BaseModel):
    items: list[Saint]
    total: int
    limit: int
    offset: int
