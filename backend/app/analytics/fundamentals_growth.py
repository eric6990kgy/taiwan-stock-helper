"""Pure revenue-growth calculation over anything shaped like a
FundamentalsDTO (a `period: str` + `revenue: Decimal | None`) -- no DB,
no HTTP, no provider dependency, so it belongs in app/analytics alongside
the rest of the deterministic layer rather than living inside a single
service. Shared by ScreenerService's revenue_growth_gt filter, Phase 7's
growth_score (app/analytics/scoring.py), and Phase 7 Part 2's
REVENUE_GROWTH_POSITIVE/REVENUE_GROWTH_ACCELERATING signals (signals.py),
instead of being written a fourth time. Deliberately duck-typed (a local
Protocol, not an import of app.providers.market_data_provider.FundamentalsDTO)
to keep this package independent of the provider layer, same rule as the
rest of app/analytics.
"""

from decimal import Decimal
from typing import Protocol


class _HasPeriodRevenue(Protocol):
    period: str
    revenue: Decimal | None


def revenue_growth_series(fundamentals: list[_HasPeriodRevenue]) -> list[Decimal | None]:
    """Period-over-period growth for every consecutive pair of reporting
    periods with a known revenue figure, sorted ascending by period and
    index-aligned with that sorted, revenue-filtered list (result[0] is
    always None -- there's no prior period to compare the first row
    against). A prior period with revenue == 0 yields None for that
    position, never a fabricated growth rate (same "missing data != zero"
    rule as revenue_growth_yoy)."""
    rows = sorted((f for f in fundamentals if f.revenue is not None), key=lambda f: f.period)
    result: list[Decimal | None] = [None] * len(rows)
    for i in range(1, len(rows)):
        previous, current = rows[i - 1], rows[i]
        if previous.revenue == 0:
            continue
        result[i] = (current.revenue - previous.revenue) / previous.revenue
    return result


def revenue_growth_yoy(fundamentals: list[_HasPeriodRevenue]) -> Decimal | None:
    """Compares the latest two reporting periods with a known revenue
    figure -- None if fewer than two exist, or the prior period's revenue
    is zero (never a fabricated growth rate)."""
    series = revenue_growth_series(fundamentals)
    return series[-1] if series else None
