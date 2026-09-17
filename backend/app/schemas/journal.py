from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.journal_entry import JOURNAL_CATEGORIES

_CATEGORY_PATTERN = f"^({'|'.join(JOURNAL_CATEGORIES)})$"


class JournalEntryCreate(BaseModel):
    entry_date: date = Field(default_factory=date.today)
    category: str = Field(default="OBSERVATION", pattern=_CATEGORY_PATTERN)
    asset_id: int | None = None
    recommendation_id: int | None = None
    body: str = Field(min_length=1)


class JournalEntryUpdate(BaseModel):
    entry_date: date | None = None
    category: str | None = Field(default=None, pattern=_CATEGORY_PATTERN)
    asset_id: int | None = None
    body: str | None = Field(default=None, min_length=1)


class JournalEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entry_date: date
    category: str
    asset_id: int | None
    ticker: str | None
    asset_name: str | None
    recommendation_id: int | None
    body: str
    created_at: datetime
    updated_at: datetime
