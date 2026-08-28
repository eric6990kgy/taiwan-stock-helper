"""Tests portfolio-level aggregation: weight per position, and the summary
rollup (invested capital, market value, P&L, dividends, fees, tax) across a
mix of open positions, a fully closed position, and a MANUAL_MARKET_VALUE
fund."""

from decimal import Decimal

from app.analytics.portfolio import calculate_portfolio_weight, summarize_portfolio
from app.analytics.types import Position, ValuedPosition


def valued(
    account_id,
    asset_id,
    remaining_shares,
    remaining_cost,
    market_value,
    realized_pnl="0",
    dividends="0",
    fees="0",
    tax="0",
    valuation_method="TRANSACTION_BASED",
    latest_close="0",
):
    position = Position(
        account_id=account_id,
        asset_id=asset_id,
        remaining_shares=Decimal(remaining_shares),
        remaining_cost=Decimal(remaining_cost),
        realized_pnl=Decimal(realized_pnl),
        total_dividends_received=Decimal(dividends),
        total_fees_paid=Decimal(fees),
        total_tax_paid=Decimal(tax),
    )
    market_value = Decimal(market_value)
    unrealized_pnl = market_value - position.remaining_cost
    return_pct = (unrealized_pnl / position.remaining_cost) if position.remaining_cost != 0 else None
    return ValuedPosition(
        position=position,
        latest_close=Decimal(latest_close),
        valuation_method=valuation_method,
        market_value=market_value,
        unrealized_pnl=unrealized_pnl,
        return_pct=return_pct,
    )


# ---- calculate_portfolio_weight ---------------------------------------------


def test_portfolio_weight_normal_case():
    assert calculate_portfolio_weight(Decimal("300"), Decimal("1000")) == Decimal("0.3")


def test_portfolio_weight_none_when_portfolio_empty():
    assert calculate_portfolio_weight(Decimal("0"), Decimal("0")) is None


# ---- summarize_portfolio -------------------------------------------------------


def test_summarize_portfolio_aggregates_across_open_closed_and_manual_positions():
    open_stock = valued(
        account_id=1, asset_id=1,
        remaining_shares="10", remaining_cost="1000", market_value="1200",
        realized_pnl="50", dividends="20", fees="10", tax="5",
    )
    closed_stock = valued(
        account_id=1, asset_id=2,
        remaining_shares="0", remaining_cost="0", market_value="0",
        realized_pnl="300", fees="15",
    )
    manual_fund = valued(
        account_id=2, asset_id=3,
        remaining_shares="120000", remaining_cost="120000", market_value="125000",
        valuation_method="MANUAL_MARKET_VALUE",
    )

    summary = summarize_portfolio([open_stock, closed_stock, manual_fund])

    assert summary.total_invested_capital == Decimal("121000")   # 1000 + 0 + 120000
    assert summary.total_market_value == Decimal("126200")       # 1200 + 0 + 125000
    assert summary.total_unrealized_pnl == Decimal("5200")       # 200 + 0 + 5000
    # Realized P&L includes the fully closed position even though it no
    # longer contributes to invested capital or market value.
    assert summary.total_realized_pnl == Decimal("350")          # 50 + 300 + 0
    assert summary.total_dividends_received == Decimal("20")
    assert summary.total_fees_paid == Decimal("25")              # 10 + 15
    assert summary.total_tax_paid == Decimal("5")
    assert summary.total_return_pct == Decimal("5200") / Decimal("121000")


def test_summarize_portfolio_weights_sum_to_one():
    a = valued(account_id=1, asset_id=1, remaining_shares="10", remaining_cost="1000", market_value="1200")
    b = valued(account_id=1, asset_id=2, remaining_shares="120000", remaining_cost="120000", market_value="125000")

    summary = summarize_portfolio([a, b])
    total = summary.total_market_value
    assert summary.weights[(1, 1)] == Decimal("1200") / total
    assert summary.weights[(1, 2)] == Decimal("125000") / total
    assert summary.weights[(1, 1)] + summary.weights[(1, 2)] == Decimal("1")


def test_summarize_portfolio_closed_position_has_zero_weight():
    closed = valued(account_id=1, asset_id=1, remaining_shares="0", remaining_cost="0", market_value="0", realized_pnl="300")
    open_ = valued(account_id=1, asset_id=2, remaining_shares="10", remaining_cost="1000", market_value="1200")

    summary = summarize_portfolio([closed, open_])
    assert summary.weights[(1, 1)] == Decimal("0")


def test_summarize_portfolio_empty_list():
    summary = summarize_portfolio([])
    assert summary.total_invested_capital == Decimal("0")
    assert summary.total_market_value == Decimal("0")
    assert summary.total_return_pct is None
    assert summary.weights == {}
