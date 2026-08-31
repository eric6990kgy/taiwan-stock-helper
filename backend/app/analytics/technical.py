"""Pure, deterministic technical indicators over a daily close/high/low
price series. No ORM, no Pydantic, no HTTP, no FastAPI -- same independence
rule as the rest of app/analytics (Phase 2's cost_basis/valuation/portfolio).

Design (Phase 6 Sec.10-12):
  - Every function takes a chronologically ordered (oldest-first) sequence
    and returns a SAME-LENGTH, index-aligned list: result[i] is computed
    using only input[0..i], never input[i+1:] (no look-ahead bias -- this is
    what lets these functions safely feed a future signal/backtesting
    engine without re-auditing them).
  - A value that can't yet be computed (insufficient history) is None, never
    0 or a fabricated neutral number ("missing data != zero").
  - KD uses the Taiwan-market convention (2/3 previous + 1/3 new RSV
    smoothing, not the textbook %K-then-SMA stochastic) -- twstock-research's
    own backtesting found the textbook version is wrong-signed for this
    market (Integration Report Sec.5); this module reimplements the
    convention from its definition, not by copying their code/weights.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

from app.analytics.technical_types import BollingerBandsResult, KDResult, MACDResult

TWO = Decimal(2)


def sma(values: Sequence[Decimal | None], period: int) -> list[Decimal | None]:
    """Simple moving average. A None in the input resets the window (never
    silently bridges a gap) -- in practice `values` is close prices, which
    are never None, so this only matters for chained indicators like MACD's
    signal line."""
    if period < 1:
        raise ValueError("period must be >= 1")
    result: list[Decimal | None] = [None] * len(values)
    window: list[Decimal] = []
    for i, v in enumerate(values):
        if v is None:
            window = []
            continue
        window.append(v)
        if len(window) > period:
            window.pop(0)
        if len(window) == period:
            result[i] = sum(window) / Decimal(period)
    return result


def ema(values: Sequence[Decimal | None], period: int) -> list[Decimal | None]:
    """Exponential moving average, seeded by the SMA of the first `period`
    values (the conventional seeding method) and smoothed with k = 2/(period+1)
    thereafter. A None resets the seed/window, same rationale as sma()."""
    if period < 1:
        raise ValueError("period must be >= 1")
    result: list[Decimal | None] = [None] * len(values)
    k = TWO / Decimal(period + 1)
    window: list[Decimal] = []
    prev_ema: Decimal | None = None
    seeded = False
    for i, v in enumerate(values):
        if v is None:
            window = []
            prev_ema = None
            seeded = False
            continue
        if not seeded:
            window.append(v)
            if len(window) == period:
                prev_ema = sum(window) / Decimal(period)
                result[i] = prev_ema
                seeded = True
            continue
        prev_ema = (v - prev_ema) * k + prev_ema
        result[i] = prev_ema
    return result


def rsi(closes: Sequence[Decimal], period: int = 14) -> list[Decimal | None]:
    """Wilder's RSI. The first `period` changes (period+1 closes) are needed
    before the first value; a window with no gains and no losses at all
    (perfectly flat prices) is reported as a neutral 50, not an undefined
    0/0 division or a directional 100."""
    if period < 1:
        raise ValueError("period must be >= 1")
    n = len(closes)
    result: list[Decimal | None] = [None] * n
    if n < period + 1:
        return result

    gains = [max(closes[i] - closes[i - 1], Decimal(0)) for i in range(1, n)]
    losses = [max(closes[i - 1] - closes[i], Decimal(0)) for i in range(1, n)]

    avg_gain: Decimal | None = None
    avg_loss: Decimal | None = None
    for i in range(1, n):
        change_idx = i - 1  # gains[change_idx] is the change ending at closes[i]
        if change_idx + 1 < period:
            continue
        if change_idx + 1 == period:
            avg_gain = sum(gains[:period]) / Decimal(period)
            avg_loss = sum(losses[:period]) / Decimal(period)
        else:
            avg_gain = (avg_gain * (period - 1) + gains[change_idx]) / Decimal(period)
            avg_loss = (avg_loss * (period - 1) + losses[change_idx]) / Decimal(period)

        if avg_gain == 0 and avg_loss == 0:
            result[i] = Decimal(50)  # no movement at all -- neutral, not fabricated
        elif avg_loss == 0:
            result[i] = Decimal(100)  # only gains -- maximally overbought, not a div-by-zero
        else:
            rs = avg_gain / avg_loss
            result[i] = Decimal(100) - (Decimal(100) / (Decimal(1) + rs))
    return result


def macd(closes: Sequence[Decimal], fast: int = 12, slow: int = 26, signal: int = 9) -> MACDResult:
    """MACD line = EMA(fast) - EMA(slow); signal = EMA(signal) of the MACD
    line; histogram = macd - signal. All three stay index-aligned with
    `closes`, None during warm-up."""
    fast_ema = ema(closes, fast)
    slow_ema = ema(closes, slow)
    macd_line = [
        (f - s) if f is not None and s is not None else None
        for f, s in zip(fast_ema, slow_ema)
    ]
    signal_line = ema(macd_line, signal)
    histogram = [
        (m - s) if m is not None and s is not None else None
        for m, s in zip(macd_line, signal_line)
    ]
    return MACDResult(macd_line=macd_line, signal_line=signal_line, histogram=histogram)


def bollinger_bands(closes: Sequence[Decimal], period: int = 20, num_std: Decimal = TWO) -> BollingerBandsResult:
    """Middle = SMA(period); upper/lower = middle +/- num_std * (population)
    standard deviation of the same window. A window of identical closes
    (std = 0) collapses all three bands to the same value -- a valid result,
    not an error."""
    middle = sma(closes, period)
    upper: list[Decimal | None] = [None] * len(closes)
    lower: list[Decimal | None] = [None] * len(closes)

    window: list[Decimal] = []
    for i, v in enumerate(closes):
        if v is None:
            window = []
            continue
        window.append(v)
        if len(window) > period:
            window.pop(0)
        if len(window) == period:
            mean = middle[i]
            variance = sum((x - mean) ** 2 for x in window) / Decimal(period)
            std = variance.sqrt()
            upper[i] = mean + num_std * std
            lower[i] = mean - num_std * std
    return BollingerBandsResult(upper=upper, middle=middle, lower=lower)


def kd(
    highs: Sequence[Decimal],
    lows: Sequence[Decimal],
    closes: Sequence[Decimal],
    period: int = 9,
) -> KDResult:
    """Taiwan-market KD (RSV over `period` days, then 2/3-previous +
    1/3-new smoothing for both K and D, seeded at 50/50 on the first RSV --
    the conventional TW retail-broker formula, distinct from the textbook
    stochastic oscillator's SMA-of-%K definition)."""
    if not (len(highs) == len(lows) == len(closes)):
        raise ValueError("highs, lows, and closes must be the same length")
    if period < 1:
        raise ValueError("period must be >= 1")

    n = len(closes)
    k_values: list[Decimal | None] = [None] * n
    d_values: list[Decimal | None] = [None] * n

    prev_k = Decimal(50)
    prev_d = Decimal(50)
    for i in range(n):
        if i + 1 < period:
            continue
        window_high = max(highs[i - period + 1 : i + 1])
        window_low = min(lows[i - period + 1 : i + 1])
        rng = window_high - window_low
        rsv = Decimal(50) if rng == 0 else (closes[i] - window_low) / rng * Decimal(100)

        k_today = prev_k * Decimal(2) / Decimal(3) + rsv * Decimal(1) / Decimal(3)
        d_today = prev_d * Decimal(2) / Decimal(3) + k_today * Decimal(1) / Decimal(3)

        k_values[i] = k_today
        d_values[i] = d_today
        prev_k = k_today
        prev_d = d_today

    return KDResult(k=k_values, d=d_values)


def latest_snapshot(closes: Sequence[Decimal], highs: Sequence[Decimal], lows: Sequence[Decimal]) -> dict[str, Decimal | None]:
    """Convenience wrapper for callers that only need the most-recent value
    of each P0 indicator (a Research-page snapshot, a Screener filter check)
    rather than the full index-aligned series -- computes every indicator
    once and returns just the last element of each, keyed by name. Still a
    pure function: no DB, no schema/Pydantic types."""
    if not closes:
        return {
            "sma_5": None, "sma_20": None, "ema_20": None, "rsi_14": None,
            "macd": None, "macd_signal": None, "macd_histogram": None,
            "bollinger_upper": None, "bollinger_middle": None, "bollinger_lower": None,
            "kd_k": None, "kd_d": None,
        }

    macd_result = macd(closes)
    bb = bollinger_bands(closes, 20)
    kd_result = kd(highs, lows, closes, 9)
    return {
        "sma_5": sma(closes, 5)[-1],
        "sma_20": sma(closes, 20)[-1],
        "ema_20": ema(closes, 20)[-1],
        "rsi_14": rsi(closes, 14)[-1],
        "macd": macd_result.macd_line[-1],
        "macd_signal": macd_result.signal_line[-1],
        "macd_histogram": macd_result.histogram[-1],
        "bollinger_upper": bb.upper[-1],
        "bollinger_middle": bb.middle[-1],
        "bollinger_lower": bb.lower[-1],
        "kd_k": kd_result.k[-1],
        "kd_d": kd_result.d[-1],
    }


def atr(highs: Sequence[Decimal], lows: Sequence[Decimal], closes: Sequence[Decimal], period: int = 14) -> list[Decimal | None]:
    """Average True Range (Wilder's smoothing, same recursive style as
    rsi()). True range = max(high-low, |high-prev_close|, |low-prev_close|)."""
    if not (len(highs) == len(lows) == len(closes)):
        raise ValueError("highs, lows, and closes must be the same length")
    if period < 1:
        raise ValueError("period must be >= 1")

    n = len(closes)
    result: list[Decimal | None] = [None] * n
    if n < period + 1:
        return result

    true_ranges = []
    for i in range(1, n):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        true_ranges.append(tr)

    avg_tr: Decimal | None = None
    for i in range(1, n):
        idx = i - 1
        if idx + 1 < period:
            continue
        if idx + 1 == period:
            avg_tr = sum(true_ranges[:period]) / Decimal(period)
        else:
            avg_tr = (avg_tr * (period - 1) + true_ranges[idx]) / Decimal(period)
        result[i] = avg_tr
    return result
