from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, StrictBool


class SaintUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    disabled: StrictBool


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
    review_status: str
    review_notes: str
    updated_at: datetime
