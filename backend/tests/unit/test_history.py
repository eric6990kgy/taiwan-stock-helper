from datetime import date
from decimal import Decimal

import pytest

from app.analytics.history import (
    DRAWDOWN_OK,
    DRAWDOWN_PAUSE,
    DRAWDOWN_STOP,
    EquityPoint,
    build_equity_curve,
    evaluate_drawdown,
)
from app.analytics.types import TransactionInput

PAUSE = Decimal("0.15")
STOP = Decimal("0.25")


def _buy(id, date_, asset_id, quantity, price):
    return TransactionInput(id=id, account_id=1, asset_id=asset_id, date=date_, type="BUY", quantity=quantity, price=price)


def _sell(id, date_, asset_id, quantity, price):
    return TransactionInput(id=id, account_id=1, asset_id=asset_id, date=date_, type="SELL", quantity=quantity, price=price)


# ---- build_equity_curve ----------------------------------------------------


def test_equity_curve_before_any_transaction_is_zero():
    txns = [_buy(1, date(2026, 1, 5), 100, Decimal("10"), Decimal("500"))]
    prices = {100: [(date(2026, 1, 1), Decimal("500"))]}
    curve = build_equity_curve(txns, prices, date(2026, 1, 1), date(2026, 1, 4))
    assert all(p.equity == Decimal("0") for p in curve)


def test_equity_curve_values_position_at_last_known_close():
    txns = [_buy(1, date(2026, 1, 1), 100, Decimal("10"), Decimal("500"))]
    prices = {100: [(date(2026, 1, 1), Decimal("500")), (date(2026, 1, 3), Decimal("550"))]}
    curve = build_equity_curve(txns, prices, date(2026, 1, 1), date(2026, 1, 4))
    by_date = {p.as_of: p.equity for p in curve}
    assert by_date[date(2026, 1, 1)] == Decimal("5000")  # 10 shares * 500
    assert by_date[date(2026, 1, 2)] == Decimal("5000")  # carries last known close forward
    assert by_date[date(2026, 1, 3)] == Decimal("5500")  # 10 * 550
    assert by_date[date(2026, 1, 4)] == Decimal("5500")


def test_equity_curve_excludes_asset_with_no_price_yet():
    txns = [_buy(1, date(2026, 1, 1), 100, Decimal("10"), Decimal("500"))]
    curve = build_equity_curve(txns, {}, date(2026, 1, 1), date(2026, 1, 2))
    assert all(p.equity == Decimal("0") for p in curve)


def test_equity_curve_reflects_a_later_sell():
    txns = [
        _buy(1, date(2026, 1, 1), 100, Decimal("10"), Decimal("500")),
        _sell(2, date(2026, 1, 3), 100, Decimal("10"), Decimal("550")),
    ]
    prices = {100: [(date(2026, 1, 1), Decimal("500")), (date(2026, 1, 3), Decimal("550"))]}
    curve = build_equity_curve(txns, prices, date(2026, 1, 1), date(2026, 1, 4))
    by_date = {p.as_of: p.equity for p in curve}
    assert by_date[date(2026, 1, 2)] == Decimal("5000")
    assert by_date[date(2026, 1, 3)] == Decimal("0")  # fully sold same day
    assert by_date[date(2026, 1, 4)] == Decimal("0")


def test_equity_curve_rejects_start_after_end():
    with pytest.raises(ValueError):
        build_equity_curve([], {}, date(2026, 1, 5), date(2026, 1, 1))


# ---- evaluate_drawdown ------------------------------------------------------


def test_evaluate_drawdown_empty_curve_is_none():
    assert evaluate_drawdown([], PAUSE, STOP) is None


def test_evaluate_drawdown_at_new_peak_is_ok():
    curve = [
        EquityPoint(date(2026, 1, 1), Decimal("1000")),
        EquityPoint(date(2026, 1, 2), Decimal("1100")),
    ]
    status = evaluate_drawdown(curve, PAUSE, STOP)
    assert status.action == DRAWDOWN_OK
    assert status.drawdown_pct == Decimal("0")
    assert status.peak_equity == Decimal("1100")


def test_evaluate_drawdown_pause_tier():
    curve = [
        EquityPoint(date(2026, 1, 1), Decimal("1000")),
        EquityPoint(date(2026, 1, 2), Decimal("830")),  # -17% off peak
    ]
    status = evaluate_drawdown(curve, PAUSE, STOP)
    assert status.action == DRAWDOWN_PAUSE
    assert status.peak_date == date(2026, 1, 1)


def test_evaluate_drawdown_stop_tier():
    curve = [
        EquityPoint(date(2026, 1, 1), Decimal("1000")),
        EquityPoint(date(2026, 1, 2), Decimal("700")),  # -30% off peak
    ]
    status = evaluate_drawdown(curve, PAUSE, STOP)
    assert status.action == DRAWDOWN_STOP


def test_evaluate_drawdown_recovery_after_a_dip_is_ok_again():
    curve = [
        EquityPoint(date(2026, 1, 1), Decimal("1000")),
        EquityPoint(date(2026, 1, 2), Decimal("700")),  # dipped hard
        EquityPoint(date(2026, 1, 3), Decimal("1200")),  # new peak -- today is OK
    ]
    status = evaluate_drawdown(curve, PAUSE, STOP)
    assert status.action == DRAWDOWN_OK
    assert status.peak_equity == Decimal("1200")


def test_evaluate_drawdown_zero_peak_does_not_divide_by_zero():
    curve = [EquityPoint(date(2026, 1, 1), Decimal("0"))]
    status = evaluate_drawdown(curve, PAUSE, STOP)
    assert status.action == DRAWDOWN_OK
    assert status.drawdown_pct == Decimal("0")
