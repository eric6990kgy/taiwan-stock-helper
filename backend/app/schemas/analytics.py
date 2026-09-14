from datetime import date as date_

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


class LimitViolationEntry(BaseModel):
    """One position or sector that's over its configured risk-limit
    threshold (個股訊號引擎規格書 Sec.05/07 hard constraints, confirmed
    2026-09-14). An empty list means "no violations", not "not checked"."""

    kind: str  # POSITION | SECTOR
    label: str
    weight: DecimalStr
    limit: DecimalStr


class RiskRead(BaseModel):
    sector_concentration: list[SectorConcentrationEntry]
    top_holdings: list[TopHolding]
    max_single_position_weight: DecimalStr | None
    position_limit_pct: DecimalStr
    sector_limit_pct: DecimalStr
    position_limit_violations: list[LimitViolationEntry]
    sector_limit_violations: list[LimitViolationEntry]
    note: str = (
        "Volatility is not implemented in V1. Drawdown circuit-breaker status "
        "moved to /api/analytics/drawdown, and benchmark/alpha to "
        "/api/analytics/benchmark (Phase A, confirmed 2026-09-14)."
    )


class DrawdownRead(BaseModel):
    """Portfolio drawdown-from-peak status as of today, reconstructed from
    transaction + price history (no daily snapshot job required — see
    app/analytics/history.py). action is one of OK / PAUSE_NEW_POSITIONS /
    HARD_STOP per the confirmed -15%/-25% thresholds."""

    as_of: date_
    equity: DecimalStr
    peak_equity: DecimalStr
    peak_date: date_
    drawdown_pct: DecimalStr
    action: str
    pause_threshold_pct: DecimalStr
    stop_threshold_pct: DecimalStr


class BenchmarkComparisonRead(BaseModel):
    """Portfolio return vs. the configured passive benchmark over the same
    window, and the resulting alpha. Any return field can be null — see
    app/analytics/benchmark.py's period_return() — with `note` explaining
    why (e.g. the benchmark asset hasn't been added/ingested yet)."""

    start_date: date_
    end_date: date_
    portfolio_return_pct: DecimalStr | None
    benchmark_ticker: str
    benchmark_return_pct: DecimalStr | None
    alpha_pct: DecimalStr | None
    note: str | None = None
