"""Combines a Position with a current price into market value and P&L.
Implements both of Asset.valuation_method's conventions (architecture
decision A4):

  - TRANSACTION_BASED: market_value = remaining_shares x latest_close
  - MANUAL_MARKET_VALUE: market_value = latest_close taken directly as the
    position's total value, ignoring remaining_shares (used for the Global
    ETF fund, where latest_close in price_history is a manually-entered
    total valuation, not a per-unit price).
"""

from decimal import Decimal

from app.analytics.types import Position, ValuedPosition

VALUATION_METHODS = ("TRANSACTION_BASED", "MANUAL_MARKET_VALUE")


def calculate_market_value(position: Position, latest_close: Decimal, valuation_method: str) -> Decimal:
    if valuation_method == "TRANSACTION_BASED":
        return position.remaining_shares * latest_close
    if valuation_method == "MANUAL_MARKET_VALUE":
        return latest_close
    raise ValueError(f"Unknown valuation_method: {valuation_method!r}")


def calculate_unrealized_pnl(market_value: Decimal, remaining_cost: Decimal) -> Decimal:
    return market_value - remaining_cost


def calculate_return_pct(unrealized_pnl: Decimal, remaining_cost: Decimal) -> Decimal | None:
    """Sec.36's Return formula. None (not zero, not an error) when there's no
    cost basis to divide by — a closed or never-opened position has no
    meaningful return percentage."""
    if remaining_cost == 0:
        return None
    return unrealized_pnl / remaining_cost


def value_position(position: Position, latest_close: Decimal, valuation_method: str) -> ValuedPosition:
    market_value = calculate_market_value(position, latest_close, valuation_method)
    unrealized_pnl = calculate_unrealized_pnl(market_value, position.remaining_cost)
    return ValuedPosition(
        position=position,
        latest_close=latest_close,
        valuation_method=valuation_method,
        market_value=market_value,
        unrealized_pnl=unrealized_pnl,
        return_pct=calculate_return_pct(unrealized_pnl, position.remaining_cost),
    )
