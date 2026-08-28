from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.thesis import THESIS_STATUSES

_STATUS_PATTERN = f"^({'|'.join(THESIS_STATUSES)})$"


class KeyMetric(BaseModel):
    label: str
    operator: str
    value: float


class ThesisUpsert(BaseModel):
    thesis: str | None = None
    catalysts: str | None = None
    risks: str | None = None
    key_metrics: list[KeyMetric] | None = None
    status: str = Field(default="INTACT", pattern=_STATUS_PATTERN)
    last_reviewed: date | None = None


class ThesisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    ticker: str
    thesis: str | None
    catalysts: str | None
    risks: str | None
    key_metrics: list[dict] | None
    status: str
    last_reviewed: date | None
    updated_at: datetime
