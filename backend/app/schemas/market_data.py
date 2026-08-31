from datetime import date

from pydantic import BaseModel


class MarketDataError(BaseModel):
    ticker: str
    reason: str


class MarketDataUpdateResult(BaseModel):
    status: str  # "completed" | "rate_limited"
    assets_processed: int
    succeeded: list[str]
    failed: list[MarketDataError]
    validation_warnings: list[MarketDataError]
    latest_data_date: date | None
    source: str
