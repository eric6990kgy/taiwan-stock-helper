"""Tests market value / unrealized P&L / return computation for both
valuation_method conventions (architecture decision A4)."""

from decimal import Decimal

import pytest

from app.analytics.types import Position
from app.analytics.valuation import (
    calculate_market_value,
    calculate_return_pct,
    calculate_unrealized_pnl,
    value_position,
)


def make_position(remaining_shares="10", remaining_cost="1000", average_cost="100"):
    return Position(
        account_id=1,
        asset_id=1,
        remaining_shares=Decimal(remaining_shares),
        average_cost=Decimal(average_cost),
        remaining_cost=Decimal(remaining_cost),
    )


# ---- TRANSACTION_BASED -------------------------------------------------------


def test_transaction_based_market_value_is_shares_times_price():
    pos = make_position(remaining_shares="20", remaining_cost="2200")
    mv = calculate_market_value(pos, latest_close=Decimal("130"), valuation_method="TRANSACTION_BASED")
    assert mv == Decimal("2600")


def test_transaction_based_market_value_zero_when_no_shares():
    pos = make_position(remaining_shares="0", remaining_cost="0")
    mv = calculate_market_value(pos, latest_close=Decimal("999"), valuation_method="TRANSACTION_BASED")
    assert mv == Decimal("0")


# ---- MANUAL_MARKET_VALUE ------------------------------------------------------


def test_manual_market_value_ignores_shares_and_uses_latest_close_directly():
    """Per A4: for the Global ETF fund, quantity tracks deposited principal
    (e.g. 120000 units at price=1), but market value is the manually
    entered total valuation, not quantity x price."""
    pos = make_position(remaining_shares="120000", remaining_cost="120000", average_cost="1")
    mv = calculate_market_value(pos, latest_close=Decimal("125000"), valuation_method="MANUAL_MARKET_VALUE")
    assert mv == Decimal("125000")


def test_unknown_valuation_method_raises():
    pos = make_position()
    with pytest.raises(ValueError):
        calculate_market_value(pos, latest_close=Decimal("100"), valuation_method="LIVE_QUOTE")


# ---- Unrealized P&L / Return % -------------------------------------------------


def test_unrealized_pnl():
    assert calculate_unrealized_pnl(market_value=Decimal("2600"), remaining_cost=Decimal("2200")) == Decimal("400")


def test_unrealized_pnl_can_be_negative():
    assert calculate_unrealized_pnl(market_value=Decimal("1800"), remaining_cost=Decimal("2200")) == Decimal("-400")


def test_return_pct():
    result = calculate_return_pct(unrealized_pnl=Decimal("400"), remaining_cost=Decimal("2000"))
    assert result == Decimal("0.2")


def test_return_pct_none_when_no_cost_basis():
    """A closed or never-opened position has no meaningful return % — not
    a ZeroDivisionError, not a fake 0%."""
    assert calculate_return_pct(unrealized_pnl=Decimal("0"), remaining_cost=Decimal("0")) is None


# ---- value_position() integration ----------------------------------------------


def test_value_position_transaction_based_end_to_end():
    pos = make_position(remaining_shares="20", remaining_cost="2200", average_cost="110")
    valued = value_position(pos, latest_close=Decimal("130"), valuation_method="TRANSACTION_BASED")

    assert valued.market_value == Decimal("2600")
    assert valued.unrealized_pnl == Decimal("400")
    assert valued.return_pct == Decimal("400") / Decimal("2200")


def test_value_position_manual_market_value_end_to_end():
    pos = make_position(remaining_shares="120000", remaining_cost="120000", average_cost="1")
    valued = value_position(pos, latest_close=Decimal("125000"), valuation_method="MANUAL_MARKET_VALUE")

    assert valued.market_value == Decimal("125000")
    assert valued.unrealized_pnl == Decimal("5000")
    assert valued.return_pct == Decimal("5000") / Decimal("120000")


def test_value_position_closed_position_has_zero_market_value_and_no_return_pct():
    pos = make_position(remaining_shares="0", remaining_cost="0", average_cost="110")
    valued = value_position(pos, latest_close=Decimal("999"), valuation_method="TRANSACTION_BASED")

    assert valued.market_value == Decimal("0")
    assert valued.unrealized_pnl == Decimal("0")
    assert valued.return_pct is None
