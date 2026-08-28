from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.watchlist import WATCHLIST_STATUSES

_STATUS_PATTERN = f"^({'|'.join(WATCHLIST_STATUSES)})$"


class WatchlistCreate(BaseModel):
    asset_id: int
    status: str = Field(default="WATCHING", pattern=_STATUS_PATTERN)
    reason: str | None = None
    target_metrics: dict | None = None
    entry_consideration: str | None = None
    review_date: date | None = None


class WatchlistUpdate(BaseModel):
    status: str | None = Field(default=None, pattern=_STATUS_PATTERN)
    reason: str | None = None
    target_metrics: dict | None = None
    entry_consideration: str | None = None
    review_date: date | None = None


class WatchlistRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    ticker: str
    asset_name: str
    status: str
    reason: str | None
    target_metrics: dict | None
    entry_consideration: str | None
    review_date: date | None
    created_at: datetime
    updated_at: datetime
