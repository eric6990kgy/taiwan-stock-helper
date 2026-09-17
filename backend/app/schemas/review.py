from datetime import date, datetime

from pydantic import BaseModel


class ReviewSummaryRead(BaseModel):
    """`hit_rate` is `None` (never a fabricated percentage) when `n == 0` --
    same "sample too small, say so" convention as BacktestSummary."""

    hits: int
    n: int
    hit_rate: str | None = None


class RecommendationOutcomeRead(BaseModel):
    id: int
    recommendation_id: int
    ticker: str
    asset_name: str
    action: str
    call: str
    actual_direction: str
    hit: bool
    horizon_trading_days: int
    as_of_date: date
    outcome_date: date
    from_close: str
    to_close: str
    risk_blocked: bool
    computed_at: datetime
