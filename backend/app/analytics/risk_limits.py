"""Position- and sector-concentration limit checks (個股訊號引擎規格書
Sec.05/07 — risk hard constraints confirmed with the user 2026-09-14).

Pure comparison logic only: the weights themselves are already computed by
app.analytics.portfolio / AnalyticsService.get_risk()'s existing
sector-concentration and top-holdings aggregation. No new weight math here
(same "calculation engine has no FastAPI/SQLAlchemy import" rule as the
rest of app.analytics — see cost_basis.py/portfolio.py docstrings).
"""

from dataclasses import dataclass
from decimal import Decimal

POSITION = "POSITION"
SECTOR = "SECTOR"


@dataclass(frozen=True)
class LimitViolation:
    kind: str  # POSITION | SECTOR
    label: str  # ticker (POSITION) or sector name (SECTOR)
    weight: Decimal
    limit: Decimal


def check_limits(weights: dict[str, Decimal | None], limit: Decimal, kind: str) -> list[LimitViolation]:
    """weights: label -> weight. None-weight entries (an empty portfolio
    reporting no meaningful weight) are skipped rather than compared —
    consistent with calculate_portfolio_weight's "None, not a fabricated
    0%" convention elsewhere in this codebase. Returns violations sorted
    worst-first."""
    violations = [
        LimitViolation(kind=kind, label=label if label else "(未分類)", weight=weight, limit=limit)
        for label, weight in weights.items()
        if weight is not None and weight > limit
    ]
    return sorted(violations, key=lambda v: v.weight, reverse=True)
