from datetime import datetime

from pydantic import BaseModel


class StrategyVersionRead(BaseModel):
    id: int
    version_number: int
    rules: dict
    status: str
    change_type: str
    reason: str | None
    backtest_hit_rate: str | None
    backtest_n: int | None
    created_at: datetime


class PendingStrategyChangeRead(BaseModel):
    id: int
    proposed_rules: dict
    reason: str
    backtest_before: dict | None
    backtest_after: dict | None
    status: str
    created_at: datetime
    decided_at: datetime | None


class ProposeStrategyChangeRequest(BaseModel):
    proposed_rules: dict
    reason: str
