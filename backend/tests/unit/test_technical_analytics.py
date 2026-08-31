"""app/analytics/technical.py -- pure indicator math, zero DB/HTTP/FastAPI
dependency (verified in test_technical_analytics_independence.py). Every
test here uses hand-computed or independently-verified expected values,
never a copy of the implementation's own arithmetic.
"""

from decimal import Decimal

import pytest

from app.analytics import technical as t


def D(x) -> Decimal:
    return Decimal(str(x))


def decimals(values) -> list[Decimal]:
    return [D(v) for v in values]


# ---- SMA --------------------------------------------------------------------------


def test_sma_basic():
    closes = decimals([10, 11, 12, 13, 14])
    result = t.sma(closes, 3)
    assert result == [None, None, D(11), D(12), D(13)]


def test_sma_insufficient_history_returns_all_none():
    closes = decimals([10, 11])
    assert t.sma(closes, 5) == [None, None]


def test_sma_empty_input_returns_empty():
    assert t.sma([], 5) == []


def test_sma_exactly_enough_observations():
    closes = decimals([10, 20, 30])
    result = t.sma(closes, 3)
    assert result == [None, None, D(20)]


def test_sma_constant_prices():
    closes = decimals([100] * 6)
    result = t.sma(closes, 3)
    assert result[2:] == [D(100)] * 4


def test_sma_resets_on_none_gap():
    values = [D(10), D(11), None, D(12), D(13), D(14)]
    result = t.sma(values, 3)
    # window resets at the None -- index 5 only has 3 consecutive non-None
    # values (12,13,14), same as if the series had started fresh there.
    assert result == [None, None, None, None, None, D(13)]


def test_sma_rejects_non_positive_period():
    with pytest.raises(ValueError):
        t.sma(decimals([1, 2, 3]), 0)


# ---- EMA --------------------------------------------------------------------------


def test_ema_basic_seeded_by_sma_then_smoothed():
    closes = decimals([10, 11, 12, 13, 14, 15])
    result = t.ema(closes, 3)
    # First EMA = SMA(3) of [10,11,12] = 11
    assert result[2] == D(11)
    # k = 2/(3+1) = 0.5 -> ema[3] = (13-11)*0.5 + 11 = 12
    assert result[3] == D(12)
    assert result[4] == D(13)
    assert result[5] == D(14)


def test_ema_insufficient_history_returns_all_none():
    assert t.ema(decimals([1, 2]), 5) == [None, None]


def test_ema_empty_input_returns_empty():
    assert t.ema([], 5) == []


def test_ema_constant_prices_stays_flat():
    closes = decimals([50] * 8)
    result = t.ema(closes, 4)
    assert result[3:] == [D(50)] * 5


# ---- RSI (Wilder's) ---------------------------------------------------------------


def test_rsi_needs_period_plus_one_closes():
    closes = decimals([1, 2, 3, 4])  # only 3 changes, period=5 needs 5
    assert t.rsi(closes, period=5) == [None] * 4


def test_rsi_empty_input_returns_empty():
    assert t.rsi([], period=14) == []


def test_rsi_constant_prices_is_neutral_fifty_not_zero_or_undefined():
    closes = decimals([100] * 10)
    result = t.rsi(closes, period=5)
    assert result[5:] == [D(50)] * 5  # never a fake 0, never a div-by-zero crash


def test_rsi_only_gains_is_100_not_a_division_by_zero():
    closes = decimals([100, 101, 102, 103, 104, 105])  # strictly increasing
    result = t.rsi(closes, period=5)
    assert result[5] == D(100)


def test_rsi_only_losses_is_zero():
    closes = decimals([105, 104, 103, 102, 101, 100])  # strictly decreasing
    result = t.rsi(closes, period=5)
    assert result[5] == D(0)


def test_rsi_hand_computed_first_value():
    # Classic worked example (Wilder's original RSI illustration values).
    closes = decimals([44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08, 45.89])
    result = t.rsi(closes, period=10)
    # avg_gain/avg_loss over the first 10 changes, hand-verified:
    changes = [closes[i] - closes[i - 1] for i in range(1, 11)]
    gains = [max(c, D(0)) for c in changes]
    losses = [max(-c, D(0)) for c in changes]
    avg_gain = sum(gains) / D(10)
    avg_loss = sum(losses) / D(10)
    expected_rsi = D(100) - (D(100) / (D(1) + avg_gain / avg_loss))
    assert result[10] == expected_rsi


# ---- MACD ---------------------------------------------------------------------------


def test_macd_warm_up_period_before_slow_ema_ready():
    closes = decimals(range(1, 10))  # 9 closes, slow=6 needs 6
    result = t.macd(closes, fast=3, slow=6, signal=2)
    assert result.macd_line[:5] == [None] * 5
    assert result.macd_line[5] is not None


def test_macd_signal_starts_after_enough_macd_values_exist():
    closes = decimals([10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20])
    result = t.macd(closes, fast=3, slow=5, signal=2)
    first_macd_idx = next(i for i, v in enumerate(result.macd_line) if v is not None)
    first_signal_idx = next(i for i, v in enumerate(result.signal_line) if v is not None)
    assert first_signal_idx > first_macd_idx  # signal needs `signal` MACD values first


def test_macd_histogram_is_macd_minus_signal():
    closes = decimals([10, 12, 11, 13, 15, 14, 16, 18, 17, 19, 21])
    result = t.macd(closes, fast=3, slow=5, signal=2)
    for m, s, h in zip(result.macd_line, result.signal_line, result.histogram):
        if m is not None and s is not None:
            assert h == m - s
        else:
            assert h is None


def test_macd_empty_input():
    result = t.macd([], fast=3, slow=5, signal=2)
    assert result.macd_line == []
    assert result.signal_line == []
    assert result.histogram == []


# ---- Bollinger Bands ----------------------------------------------------------------


def test_bollinger_bands_hand_computed():
    closes = decimals([10, 12, 14, 12, 10])
    result = t.bollinger_bands(closes, period=5, num_std=D(2))
    mean = sum(closes) / D(5)
    variance = sum((c - mean) ** 2 for c in closes) / D(5)
    std = variance.sqrt()
    assert result.middle[4] == mean
    assert result.upper[4] == mean + D(2) * std
    assert result.lower[4] == mean - D(2) * std


def test_bollinger_bands_zero_std_collapses_all_three_bands():
    closes = decimals([100] * 6)
    result = t.bollinger_bands(closes, period=4)
    assert result.upper[3] == result.middle[3] == result.lower[3] == D(100)


def test_bollinger_bands_insufficient_history():
    closes = decimals([1, 2, 3])
    result = t.bollinger_bands(closes, period=20)
    assert all(v is None for v in result.upper + result.middle + result.lower)


def test_bollinger_bands_empty_input():
    result = t.bollinger_bands([], period=20)
    assert result.upper == [] and result.middle == [] and result.lower == []


# ---- KD (Taiwan convention) -----------------------------------------------------------


def test_kd_warm_up_period():
    highs = decimals([10, 11, 12, 13])
    lows = decimals([8, 9, 10, 11])
    closes = decimals([9, 10, 11, 12])
    result = t.kd(highs, lows, closes, period=9)
    assert result.k == [None] * 4
    assert result.d == [None] * 4


def test_kd_hand_computed_first_value_seeded_at_fifty():
    highs = decimals([10, 11, 12, 13, 14])
    lows = decimals([8, 9, 10, 11, 12])
    closes = decimals([9, 10, 11, 12, 13])
    result = t.kd(highs, lows, closes, period=5)

    rsv = (closes[4] - min(lows)) / (max(highs) - min(lows)) * D(100)
    expected_k = D(50) * D(2) / D(3) + rsv * D(1) / D(3)
    expected_d = D(50) * D(2) / D(3) + expected_k * D(1) / D(3)
    assert result.k[4] == expected_k
    assert result.d[4] == expected_d


def test_kd_zero_range_uses_neutral_fifty_rsv_not_division_by_zero():
    highs = decimals([10] * 5)
    lows = decimals([10] * 5)  # high == low every day -> zero range
    closes = decimals([10] * 5)
    result = t.kd(highs, lows, closes, period=5)
    # RSV=50 (neutral) each day -> K/D converge toward 50, never crash.
    assert result.k[4] is not None
    assert result.d[4] is not None


def test_kd_mismatched_lengths_raises():
    with pytest.raises(ValueError):
        t.kd(decimals([1, 2]), decimals([1]), decimals([1, 2]), period=1)


def test_kd_empty_input():
    result = t.kd([], [], [], period=9)
    assert result.k == [] and result.d == []


# ---- ATR --------------------------------------------------------------------------


def test_atr_hand_computed_first_value():
    highs = decimals([12, 13, 14, 13, 15, 16])
    lows = decimals([10, 11, 12, 11, 13, 14])
    closes = decimals([11, 12, 13, 12, 14, 15])
    result = t.atr(highs, lows, closes, period=5)

    true_ranges = []
    for i in range(1, 6):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        true_ranges.append(tr)
    expected = sum(true_ranges) / D(5)
    assert result[5] == expected


def test_atr_insufficient_history():
    highs, lows, closes = decimals([1, 2]), decimals([1, 2]), decimals([1, 2])
    assert t.atr(highs, lows, closes, period=14) == [None, None]


# ---- Look-ahead bias: the core Sec.12 guarantee ------------------------------------


@pytest.mark.parametrize(
    "fn_name",
    ["sma_case", "ema_case", "rsi_case", "macd_case", "bollinger_case", "kd_case"],
)
def test_no_look_ahead_bias(fn_name):
    """Changing a FUTURE observation must never change an indicator's
    already-computed HISTORICAL values -- this is what makes these safe
    inputs to a future signal/backtesting engine without re-auditing."""
    base_closes = decimals([10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20])
    base_highs = [c + D(1) for c in base_closes]
    base_lows = [c - D(1) for c in base_closes]

    mutated_closes = list(base_closes)
    mutated_closes[-1] = D(9999)  # only the LAST (future-most) observation changes
    mutated_highs = list(base_highs)
    mutated_highs[-1] = D(9999)
    mutated_lows = list(base_lows)
    mutated_lows[-1] = D(1)

    cutoff = len(base_closes) - 1  # every index strictly before the mutated one

    if fn_name == "sma_case":
        a, b = t.sma(base_closes, 5), t.sma(mutated_closes, 5)
    elif fn_name == "ema_case":
        a, b = t.ema(base_closes, 5), t.ema(mutated_closes, 5)
    elif fn_name == "rsi_case":
        a, b = t.rsi(base_closes, 5), t.rsi(mutated_closes, 5)
    elif fn_name == "macd_case":
        ra, rb = t.macd(base_closes, 3, 5, 2), t.macd(mutated_closes, 3, 5, 2)
        a, b = ra.macd_line, rb.macd_line
    elif fn_name == "bollinger_case":
        ra, rb = t.bollinger_bands(base_closes, 5), t.bollinger_bands(mutated_closes, 5)
        a, b = ra.middle, rb.middle
    elif fn_name == "kd_case":
        ra = t.kd(base_highs, base_lows, base_closes, period=5)
        rb = t.kd(mutated_highs, mutated_lows, mutated_closes, period=5)
        a, b = ra.k, rb.k

    assert a[:cutoff] == b[:cutoff]
