from pydantic import BaseModel

from app.schemas.common import DecimalStr


class AllocationEntry(BaseModel):
    account_id: int
    asset_id: int
    ticker: str
    asset_name: str
    market_value: DecimalStr
    weight: DecimalStr | None


class AllocationRead(BaseModel):
    total_market_value: DecimalStr
    entries: list[AllocationEntry]


class PerformanceRead(BaseModel):
    """A current-snapshot view of portfolio performance, not a time series.

    The calculation engine (Phase 2) has no historical portfolio-value replay
    yet — that would need per-day valuation across the whole transaction
    history, which wasn't built or approved in Phase 2. This endpoint
    intentionally reuses PortfolioSummary rather than inventing a time-series
    calculation; `note` says so explicitly instead of silently under-delivering
    on what "/api/analytics/performance" implies.
    """

    total_market_value: DecimalStr
    remaining_cost_basis: DecimalStr
    realized_pnl: DecimalStr
    unrealized_pnl: DecimalStr
    total_pnl: DecimalStr
    total_return_pct: DecimalStr | None
    note: str = "Snapshot only — historical time-series performance is not implemented in V1."


class SectorConcentrationEntry(BaseModel):
    sector: str | None
    market_value: DecimalStr
    weight: DecimalStr | None


class TopHolding(BaseModel):
    ticker: str
    asset_name: str
    market_value: DecimalStr
    weight: DecimalStr | None


class RiskRead(BaseModel):
    sector_concentration: list[SectorConcentrationEntry]
    top_holdings: list[TopHolding]
    max_single_position_weight: DecimalStr | None
    note: str = "Volatility and maximum drawdown are not implemented in V1 (PRD roadmap item)."
