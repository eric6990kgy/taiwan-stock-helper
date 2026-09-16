"""Tests for app/analytics/signal_backtest.py's walk-forward hit-rate
check (Phase 8)."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.analytics.signal_backtest import walk_forward_hit_rate
from app.analytics.signal_rules import DEFAULT_RULES


@dataclass
class Point:
    date: date
    close: Decimal


D0 = date(2026, 1, 1)


def rising_series(n: int, start_price: int = 100, step: int = 1) -> list[Point]:
    return [Point(D0 + timedelta(days=i), Decimal(str(start_price + step * i))) for i in range(n)]


def test_insufficient_history_reports_zero_sample_not_a_fabricated_rate():
    result = walk_forward_hit_rate(rising_series(30), DEFAULT_RULES)
    assert result.n == 0
    assert result.hit_rate is None


def test_pure_uptrend_scores_a_high_hit_rate_for_bullish_calls():
    """A relentless, noise-free uptrend: whenever the signal engine calls
    BULLISH, price should indeed be higher `horizon` days later -- a
    strong, easy-to-reason-about sanity check on the harness itself."""
    points = rising_series(140, start_price=100, step=2)
    result = walk_forward_hit_rate(points, DEFAULT_RULES, horizon=5, deadzone_pct=Decimal("1"))
    assert result.n > 0
    assert result.hit_rate is not None
    assert result.hit_rate >= Decimal("0.9")


def test_pure_downtrend_scores_a_high_hit_rate_for_bearish_calls():
    points = rising_series(140, start_price=500, step=-2)
    result = walk_forward_hit_rate(points, DEFAULT_RULES, horizon=5, deadzone_pct=Decimal("1"))
    assert result.n > 0
    assert result.hit_rate is not None
    assert result.hit_rate >= Decimal("0.9")


def test_flat_prices_never_produce_a_scored_call():
    """Flat prices -> every technical signal is NEUTRAL -> overall_status
    is NEUTRAL -> excluded from the hit-rate tally entirely (only
    BULLISH/BEARISH calls are scored)."""
    points = [Point(D0 + timedelta(days=i), Decimal("100")) for i in range(140)]
    result = walk_forward_hit_rate(points, DEFAULT_RULES)
    assert result.n == 0
    assert result.hit_rate is None


def test_horizon_and_deadzone_are_recorded_on_the_result():
    result = walk_forward_hit_rate(rising_series(140, step=2), DEFAULT_RULES, horizon=10, deadzone_pct=Decimal("2"))
    assert result.horizon == 10
    assert result.deadzone_pct == Decimal("2")
