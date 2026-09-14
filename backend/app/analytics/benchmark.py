"""Alpha vs. a passive benchmark (個股訊號引擎規格書 Goal — confirmed with the
user 2026-09-14): because the user already holds broad-market/0050 exposure
directly and separately, the individual-stock system's success metric has
to be excess return over that benchmark, not a raw win rate or absolute
return — if it can't beat the benchmark, the extra risk of individual-stock
picking isn't worth taking on top of what's already held passively.

Pure functions — same no-FastAPI/SQLAlchemy rule as the rest of
app.analytics. See AnalyticsService.get_benchmark_comparison() for how the
period start/end prices are actually sourced (portfolio equity curve vs.
the benchmark asset's own price history).
"""

from decimal import Decimal


def period_return(start_value: Decimal | None, end_value: Decimal | None) -> Decimal | None:
    """None (never a fabricated 0%) when either value is missing or the
    starting value is zero — same "None over a fake number" convention used
    throughout this codebase (see PerformanceRead / calculate_portfolio_weight)."""
    if start_value is None or end_value is None or start_value == 0:
        return None
    return (end_value - start_value) / start_value


def calculate_alpha(portfolio_return: Decimal | None, benchmark_return: Decimal | None) -> Decimal | None:
    """Excess return = portfolio return - benchmark return over the same
    period. None propagates: alpha is only meaningful when both sides are
    known, never manufactured from a missing side."""
    if portfolio_return is None or benchmark_return is None:
        return None
    return portfolio_return - benchmark_return
