from pydantic import BaseModel

from app.schemas.common import DecimalStr


class ScreenerResult(BaseModel):
    """Deliberately no verdict field (no BUY/SELL) — Sec.17: the screener
    reports which criteria are met, not what to do about it."""

    ticker: str
    asset_name: str
    revenue_growth_yoy: DecimalStr | None
    roe: DecimalStr | None
    pe_ratio: DecimalStr | None
    meets_criteria: bool
