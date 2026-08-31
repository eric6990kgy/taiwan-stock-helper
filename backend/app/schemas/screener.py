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
    # Phase 6 P0 fields -- filled in only when the corresponding filter (or
    # its prerequisite data) is actually usable for this asset; None means
    # "not available", never a fabricated pass/fail.
    foreign_net_buy: int | None = None
    rsi_14: DecimalStr | None = None
    above_sma_20: bool | None = None
    meets_criteria: bool
