"""Hand-computed tests for app/analytics/signals.py -- every signal
function's BULLISH/BEARISH/NEUTRAL/UNAVAILABLE boundary, plus an explicit
no-look-ahead check per signal type that takes a dated series."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.analytics import signals
from app.analytics.signal_types import BEARISH, BULLISH, NEUTRAL, UNAVAILABLE


@dataclass
class Point:
    date: date
    close: Decimal


@dataclass
class Flow:
    date: date
    foreign_net: int | None
    investment_trust_net: int | None = None


@dataclass
class Fund:
    period: str
    revenue: Decimal | None


D0 = date(2026, 1, 1)


def days(points_values: list, start: date = D0) -> list[Point]:
    return [Point(date=start + timedelta(days=i), close=Decimal(str(v))) for i, v in enumerate(points_values)]


# ---- price_above_sma_signal -----------------------------------------------


def test_price_above_sma_bullish():
    points = days([100] * 19 + [101])  # sma20 = (100*19 + 101)/20
    signal = signals.price_above_sma_signal(points, 20, points[-1].date)
    assert signal.status == BULLISH


def test_price_above_sma_bearish():
    points = days([100] * 19 + [99])
    signal = signals.price_above_sma_signal(points, 20, points[-1].date)
    assert signal.status == BEARISH


def test_price_above_sma_neutral_when_exactly_equal():
    points = days([100] * 20)
    signal = signals.price_above_sma_signal(points, 20, points[-1].date)
    assert signal.status == NEUTRAL


def test_price_above_sma_unavailable_when_insufficient_history():
    points = days([100] * 5)
    signal = signals.price_above_sma_signal(points, 20, points[-1].date)
    assert signal.status == UNAVAILABLE
    assert signal.threshold is None  # the SMA itself -- unknown, not the close


def test_price_above_sma_ignores_future_rows():
    base = days([100] * 19 + [101])
    as_of = base[-1].date
    with_future = base + [Point(date=as_of + timedelta(days=1), close=Decimal("1"))]
    assert signals.price_above_sma_signal(with_future, 20, as_of) == signals.price_above_sma_signal(base, 20, as_of)


# ---- rsi_bullish_signal -----------------------------------------------------


def test_rsi_bullish_when_above_50():
    points = days([100 + i for i in range(20)])  # steadily rising -- RSI > 50
    signal = signals.rsi_bullish_signal(points, points[-1].date)
    assert signal.status == BULLISH


def test_rsi_bearish_when_below_50():
    points = days([100 - i for i in range(20)])  # steadily falling -- RSI < 50
    signal = signals.rsi_bullish_signal(points, points[-1].date)
    assert signal.status == BEARISH


def test_rsi_neutral_when_exactly_50_flat_prices():
    points = days([100] * 20)  # no movement at all -- technical.rsi() returns 50
    signal = signals.rsi_bullish_signal(points, points[-1].date)
    assert signal.status == NEUTRAL
    assert signal.value == Decimal(50)


def test_rsi_unavailable_when_insufficient_history():
    points = days([100] * 5)
    signal = signals.rsi_bullish_signal(points, points[-1].date)
    assert signal.status == UNAVAILABLE


def test_rsi_ignores_future_rows():
    base = days([100 + i for i in range(20)])
    as_of = base[-1].date
    with_future = base + [Point(date=as_of + timedelta(days=1), close=Decimal("1"))]
    assert signals.rsi_bullish_signal(with_future, as_of) == signals.rsi_bullish_signal(base, as_of)


# ---- macd_bullish_signal -----------------------------------------------------


def test_macd_bullish_when_histogram_positive():
    # Flat, then a late sharp rise -- fast EMA reacts before the signal
    # line catches up, so the histogram is clearly positive (a pure
    # constant-slope trend instead would let signal line fully catch up
    # to macd line, converging the histogram back toward zero).
    points = days([100] * 32 + [100 + 3 * i for i in range(1, 9)])
    signal = signals.macd_bullish_signal(points, points[-1].date)
    assert signal.status == BULLISH


def test_macd_bearish_when_histogram_negative():
    points = days([200] * 32 + [200 - 3 * i for i in range(1, 9)])
    signal = signals.macd_bullish_signal(points, points[-1].date)
    assert signal.status == BEARISH


def test_macd_unavailable_during_warmup():
    points = days([100] * 5)
    signal = signals.macd_bullish_signal(points, points[-1].date)
    assert signal.status == UNAVAILABLE


def test_macd_ignores_future_rows():
    base = days([100 + i * 2 for i in range(40)])
    as_of = base[-1].date
    with_future = base + [Point(date=as_of + timedelta(days=1), close=Decimal("1"))]
    assert signals.macd_bullish_signal(with_future, as_of) == signals.macd_bullish_signal(base, as_of)


# ---- foreign_net_buying_signal / investment_trust_net_buying_signal --------


def test_foreign_net_buying_bullish():
    flows = [Flow(D0 + timedelta(days=i), foreign_net=100) for i in range(5)]
    signal = signals.foreign_net_buying_signal(flows, flows[-1].date)
    assert signal.status == BULLISH
    assert signal.value == Decimal(500)


def test_foreign_net_buying_bearish():
    flows = [Flow(D0 + timedelta(days=i), foreign_net=-100) for i in range(5)]
    signal = signals.foreign_net_buying_signal(flows, flows[-1].date)
    assert signal.status == BEARISH


def test_foreign_net_buying_neutral_when_exactly_zero():
    flows = [Flow(D0 + timedelta(days=i), foreign_net=100) for i in range(4)] + [Flow(D0 + timedelta(days=4), foreign_net=-400)]
    signal = signals.foreign_net_buying_signal(flows, flows[-1].date)
    assert signal.status == NEUTRAL


def test_foreign_net_buying_unavailable_when_fewer_than_window_rows():
    flows = [Flow(D0 + timedelta(days=i), foreign_net=100) for i in range(3)]
    signal = signals.foreign_net_buying_signal(flows, flows[-1].date)
    assert signal.status == UNAVAILABLE


def test_foreign_net_buying_unavailable_when_a_row_in_window_is_incomplete():
    flows = [Flow(D0 + timedelta(days=i), foreign_net=100) for i in range(4)] + [Flow(D0 + timedelta(days=4), foreign_net=None)]
    signal = signals.foreign_net_buying_signal(flows, flows[-1].date)
    assert signal.status == UNAVAILABLE


def test_foreign_net_buying_ignores_future_rows():
    base = [Flow(D0 + timedelta(days=i), foreign_net=100) for i in range(5)]
    as_of = base[-1].date
    with_future = base + [Flow(as_of + timedelta(days=1), foreign_net=-99999)]
    assert signals.foreign_net_buying_signal(with_future, as_of) == signals.foreign_net_buying_signal(base, as_of)


def test_investment_trust_net_buying_bullish():
    flows = [Flow(D0 + timedelta(days=i), foreign_net=0, investment_trust_net=50) for i in range(5)]
    signal = signals.investment_trust_net_buying_signal(flows, flows[-1].date)
    assert signal.status == BULLISH


# ---- revenue_growth_positive_signal / revenue_growth_accelerating_signal ---


def test_revenue_growth_positive_bullish():
    funds = [Fund("2025-06", Decimal("100")), Fund("2026-06", Decimal("120"))]
    signal = signals.revenue_growth_positive_signal(funds, date(2026, 9, 1))
    assert signal.status == BULLISH


def test_revenue_growth_positive_bearish():
    funds = [Fund("2025-06", Decimal("100")), Fund("2026-06", Decimal("80"))]
    signal = signals.revenue_growth_positive_signal(funds, date(2026, 9, 1))
    assert signal.status == BEARISH


def test_revenue_growth_positive_neutral_when_exactly_zero():
    funds = [Fund("2025-06", Decimal("100")), Fund("2026-06", Decimal("100"))]
    signal = signals.revenue_growth_positive_signal(funds, date(2026, 9, 1))
    assert signal.status == NEUTRAL


def test_revenue_growth_positive_unavailable_with_fewer_than_two_periods():
    funds = [Fund("2026-06", Decimal("100"))]
    signal = signals.revenue_growth_positive_signal(funds, date(2026, 9, 1))
    assert signal.status == UNAVAILABLE


def test_revenue_growth_positive_unavailable_when_prior_revenue_is_zero():
    funds = [Fund("2025-06", Decimal("0")), Fund("2026-06", Decimal("100"))]
    signal = signals.revenue_growth_positive_signal(funds, date(2026, 9, 1))
    assert signal.status == UNAVAILABLE


def test_revenue_growth_accelerating_bullish():
    funds = [Fund("2024-06", Decimal("100")), Fund("2025-06", Decimal("110")), Fund("2026-06", Decimal("140"))]
    signal = signals.revenue_growth_accelerating_signal(funds, date(2026, 9, 1))
    assert signal.status == BULLISH


def test_revenue_growth_accelerating_bearish():
    funds = [Fund("2024-06", Decimal("100")), Fund("2025-06", Decimal("140")), Fund("2026-06", Decimal("110"))]
    signal = signals.revenue_growth_accelerating_signal(funds, date(2026, 9, 1))
    assert signal.status == BEARISH


def test_revenue_growth_accelerating_neutral_when_unchanged():
    funds = [Fund("2024-06", Decimal("100")), Fund("2025-06", Decimal("110")), Fund("2026-06", Decimal("121"))]
    signal = signals.revenue_growth_accelerating_signal(funds, date(2026, 9, 1))
    assert signal.status == NEUTRAL


def test_revenue_growth_accelerating_unavailable_with_fewer_than_three_periods():
    funds = [Fund("2025-06", Decimal("100")), Fund("2026-06", Decimal("110"))]
    signal = signals.revenue_growth_accelerating_signal(funds, date(2026, 9, 1))
    assert signal.status == UNAVAILABLE


# ---- composite_score_signal --------------------------------------------------


def test_composite_score_bullish_at_60_exactly():
    signal = signals.composite_score_signal(Decimal("60"), date(2026, 9, 1))
    assert signal.status == BULLISH


def test_composite_score_neutral_just_below_60():
    signal = signals.composite_score_signal(Decimal("59.99"), date(2026, 9, 1))
    assert signal.status == NEUTRAL


def test_composite_score_bearish_at_40_exactly():
    signal = signals.composite_score_signal(Decimal("40"), date(2026, 9, 1))
    assert signal.status == BEARISH


def test_composite_score_neutral_just_above_40():
    signal = signals.composite_score_signal(Decimal("40.01"), date(2026, 9, 1))
    assert signal.status == NEUTRAL


def test_composite_score_unavailable_when_none():
    signal = signals.composite_score_signal(None, date(2026, 9, 1))
    assert signal.status == UNAVAILABLE


# ---- overall_status ----------------------------------------------------------


def test_overall_status_majority_bullish():
    sigs = [
        signals.composite_score_signal(Decimal("70"), D0),
        signals.composite_score_signal(Decimal("70"), D0),
        signals.composite_score_signal(Decimal("20"), D0),
    ]
    assert signals.overall_status(sigs) == BULLISH


def test_overall_status_tie_is_neutral():
    sigs = [signals.composite_score_signal(Decimal("70"), D0), signals.composite_score_signal(Decimal("20"), D0)]
    assert signals.overall_status(sigs) == NEUTRAL


def test_overall_status_all_unavailable():
    sigs = [signals.composite_score_signal(None, D0), signals.composite_score_signal(None, D0)]
    assert signals.overall_status(sigs) == UNAVAILABLE


def test_overall_status_ignores_unavailable_when_others_present():
    sigs = [
        signals.composite_score_signal(Decimal("70"), D0),
        signals.composite_score_signal(None, D0),
    ]
    assert signals.overall_status(sigs) == BULLISH
