"""Portfolio-level aggregation across many ValuedPositions: invested capital,
total market value, portfolio weight per position, and the P&L rollups
Dashboard needs (PRD Sec.8/Sec.36). Deliberately thin — allocation-by-sector,
performance-over-time, and risk/concentration are out of Phase 2 scope.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.analytics.types import ValuedPosition


def calculate_portfolio_weight(market_value: Decimal, total_portfolio_value: Decimal) -> Decimal | None:
    """Sec.36's Weight formula. None when the portfolio is empty — there's no
    meaningful weight to report, not a divide-by-zero to hide behind 0%."""
    if total_portfolio_value == 0:
        return None
    return market_value / total_portfolio_value


@dataclass
class PortfolioSummary:
    total_invested_capital: Decimal
    total_market_value: Decimal
    total_unrealized_pnl: Decimal
    total_realized_pnl: Decimal
    total_dividends_received: Decimal
    total_fees_paid: Decimal
    total_tax_paid: Decimal
    total_return_pct: Decimal | None
    weights: dict[tuple[int, int], Decimal | None]  # (account_id, asset_id) -> weight


def summarize_portfolio(valued_positions: list[ValuedPosition]) -> PortfolioSummary:
    total_invested_capital = sum((vp.position.remaining_cost for vp in valued_positions), Decimal("0"))
    total_market_value = sum((vp.market_value for vp in valued_positions), Decimal("0"))
    total_unrealized_pnl = sum((vp.unrealized_pnl for vp in valued_positions), Decimal("0"))
    # Realized P&L accumulates over the position's whole history, including
    # positions now fully closed (remaining_shares == 0) — those still carry
    # their realized_pnl and must count here even though they contribute
    # nothing to market value or invested capital.
    total_realized_pnl = sum((vp.position.realized_pnl for vp in valued_positions), Decimal("0"))
    total_dividends_received = sum((vp.position.total_dividends_received for vp in valued_positions), Decimal("0"))
    total_fees_paid = sum((vp.position.total_fees_paid for vp in valued_positions), Decimal("0"))
    total_tax_paid = sum((vp.position.total_tax_paid for vp in valued_positions), Decimal("0"))

    weights = {
        (vp.position.account_id, vp.position.asset_id): calculate_portfolio_weight(vp.market_value, total_market_value)
        for vp in valued_positions
    }

    total_return_pct = (
        total_unrealized_pnl / total_invested_capital if total_invested_capital != 0 else None
    )

    return PortfolioSummary(
        total_invested_capital=total_invested_capital,
        total_market_value=total_market_value,
        total_unrealized_pnl=total_unrealized_pnl,
        total_realized_pnl=total_realized_pnl,
        total_dividends_received=total_dividends_received,
        total_fees_paid=total_fees_paid,
        total_tax_paid=total_tax_paid,
        total_return_pct=total_return_pct,
        weights=weights,
    )
