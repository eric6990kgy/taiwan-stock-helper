from datetime import date, datetime

from pydantic import BaseModel


class TriggeredSignalRead(BaseModel):
    id: str
    category: str
    name: str
    status: str
    explanation: str


class RecommendationRead(BaseModel):
    """A recommendation is conditional language only (關注/考慮增加關注度/
    考慮減碼) -- never a BUY/SELL instruction. risk_blocked/risk_block_reason
    are always present (not just on request) so a blocked recommendation
    can never be mistaken for a clear one by a client that forgets to check
    a separate field."""

    id: int
    ticker: str
    asset_name: str
    action: str
    previous_status: str | None
    new_status: str
    triggered_signals: list[TriggeredSignalRead]
    risk_blocked: bool
    risk_block_reason: str | None
    composite_score: str | None = None
    regime: str | None = None
    strategy_version_id: int
    created_at: datetime


class DailyScanResultRead(BaseModel):
    as_of: date
    recommendations: list[RecommendationRead]
