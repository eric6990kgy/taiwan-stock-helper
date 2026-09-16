"""Pure, deterministic BULLISH/BEARISH/NEUTRAL/UNAVAILABLE signals (Phase 7
Part 2). No ORM, no Pydantic, no HTTP, no FastAPI -- same independence rule
as the rest of app/analytics.

Design:
  - Every signal function that takes a dated series (price points,
    institutional flow rows) does its OWN `date <= as_of` filtering
    internally, given the full history -- this is what guarantees no
    look-ahead bias: appending rows dated after `as_of` can never change
    the signal computed for that `as_of` (Sec.12 of the Phase 6 spec,
    extended here to signals).
  - A signal is UNAVAILABLE (never a fabricated NEUTRAL) whenever its
    inputs are insufficient -- not enough history, a None value inside the
    window, no fundamentals data. "Missing data != a reading."
  - No BUY/SELL vocabulary anywhere (spec Sec.7) -- BULLISH/BEARISH/NEUTRAL
    describe the indicator's own reading, not a trading instruction.
"""

from collections import Counter
from datetime import date as date_
from decimal import Decimal
from typing import Protocol, Sequence

from app.analytics import technical
from app.analytics.fundamentals_growth import revenue_growth_series, revenue_growth_yoy
from app.analytics.signal_types import BEARISH, BULLISH, NEUTRAL, UNAVAILABLE, Signal

ZERO = Decimal(0)
FIFTY = Decimal(50)


class _HasDateClose(Protocol):
    date: date_
    close: Decimal


class _HasDateForeignNet(Protocol):
    date: date_
    foreign_net: int | None


class _HasDateTrustNet(Protocol):
    date: date_
    investment_trust_net: int | None


class _HasPeriodRevenue(Protocol):
    period: str
    revenue: Decimal | None


def _closes_as_of(points: Sequence[_HasDateClose], as_of: date_) -> list[Decimal]:
    rows = sorted((p for p in points if p.date <= as_of), key=lambda p: p.date)
    return [p.close for p in rows]


def price_above_sma_signal(points: Sequence[_HasDateClose], period: int, as_of: date_) -> Signal:
    """BULLISH if the as-of close is above its SMA(period), BEARISH if
    below, NEUTRAL if exactly equal. UNAVAILABLE if there isn't yet
    `period` days of history as of `as_of`."""
    signal_id = f"PRICE_ABOVE_SMA{period}"
    name = f"股價站上{period}日均線" if period else "股價站上均線"
    closes = _closes_as_of(points, as_of)
    if not closes:
        return Signal(signal_id, "TECHNICAL", name, UNAVAILABLE, None, None, as_of, "尚無價格資料", "CALCULATED")

    sma_value = technical.sma(closes, period)[-1]
    close = closes[-1]
    if sma_value is None:
        return Signal(signal_id, "TECHNICAL", name, UNAVAILABLE, close, None, as_of, f"歷史資料不足 {period} 日", "CALCULATED")

    if close > sma_value:
        status, explanation = BULLISH, f"股價 {close} 站上 {period} 日均線 {sma_value:.2f}"
    elif close < sma_value:
        status, explanation = BEARISH, f"股價 {close} 跌破 {period} 日均線 {sma_value:.2f}"
    else:
        status, explanation = NEUTRAL, f"股價與 {period} 日均線持平於 {sma_value:.2f}"
    return Signal(signal_id, "TECHNICAL", name, status, close, sma_value, as_of, explanation, "CALCULATED")


def rsi_bullish_signal(points: Sequence[_HasDateClose], as_of: date_, period: int = 14) -> Signal:
    """BULLISH if RSI > 50 (more gains than losses over the window),
    BEARISH if < 50, NEUTRAL if exactly 50. UNAVAILABLE during warm-up."""
    closes = _closes_as_of(points, as_of)
    if not closes:
        return Signal("RSI_BULLISH", "TECHNICAL", "RSI 動能", UNAVAILABLE, None, FIFTY, as_of, "尚無價格資料", "CALCULATED")

    rsi_value = technical.rsi(closes, period)[-1]
    if rsi_value is None:
        return Signal("RSI_BULLISH", "TECHNICAL", "RSI 動能", UNAVAILABLE, None, FIFTY, as_of, f"歷史資料不足 {period} 日", "CALCULATED")

    if rsi_value > FIFTY:
        status, explanation = BULLISH, f"RSI {rsi_value:.1f} 高於 50，動能偏多"
    elif rsi_value < FIFTY:
        status, explanation = BEARISH, f"RSI {rsi_value:.1f} 低於 50，動能偏空"
    else:
        status, explanation = NEUTRAL, "RSI 為 50，動能中性"
    return Signal("RSI_BULLISH", "TECHNICAL", "RSI 動能", status, rsi_value, FIFTY, as_of, explanation, "CALCULATED")


def macd_bullish_signal(points: Sequence[_HasDateClose], as_of: date_) -> Signal:
    """BULLISH if the MACD histogram (MACD line - signal line) is positive,
    BEARISH if negative, NEUTRAL if exactly zero. UNAVAILABLE during
    warm-up (needs enough history for the slow EMA + signal line)."""
    closes = _closes_as_of(points, as_of)
    if not closes:
        return Signal("MACD_BULLISH", "TECHNICAL", "MACD 動能", UNAVAILABLE, None, ZERO, as_of, "尚無價格資料", "CALCULATED")

    histogram = technical.macd(closes).histogram[-1]
    if histogram is None:
        return Signal("MACD_BULLISH", "TECHNICAL", "MACD 動能", UNAVAILABLE, None, ZERO, as_of, "歷史資料不足", "CALCULATED")

    if histogram > ZERO:
        status, explanation = BULLISH, f"MACD 柱狀圖 {histogram:.2f} 為正，動能偏多"
    elif histogram < ZERO:
        status, explanation = BEARISH, f"MACD 柱狀圖 {histogram:.2f} 為負，動能偏空"
    else:
        status, explanation = NEUTRAL, "MACD 柱狀圖為零，動能中性"
    return Signal("MACD_BULLISH", "TECHNICAL", "MACD 動能", status, histogram, ZERO, as_of, explanation, "CALCULATED")


def _net_buying_signal(
    signal_id: str,
    name: str,
    flows: Sequence,
    net_attr: str,
    as_of: date_,
    window: int,
) -> Signal:
    rows = sorted((f for f in flows if f.date <= as_of), key=lambda f: f.date)[-window:]
    if len(rows) < window or any(getattr(r, net_attr) is None for r in rows):
        return Signal(signal_id, "INSTITUTIONAL", name, UNAVAILABLE, None, ZERO, as_of, f"近 {window} 個交易日資料不足", "CALCULATED")

    total = sum(getattr(r, net_attr) for r in rows)
    if total > 0:
        status, explanation = BULLISH, f"近 {window} 個交易日合計買超 {total:,} 股"
    elif total < 0:
        status, explanation = BEARISH, f"近 {window} 個交易日合計賣超 {abs(total):,} 股"
    else:
        status, explanation = NEUTRAL, f"近 {window} 個交易日買賣相抵"
    return Signal(signal_id, "INSTITUTIONAL", name, status, Decimal(total), ZERO, as_of, explanation, "CALCULATED")


def foreign_net_buying_signal(flows: Sequence[_HasDateForeignNet], as_of: date_, window: int = 5) -> Signal:
    """BULLISH if foreign investors were net buyers over the trailing
    `window` trading days (summed), BEARISH if net sellers, NEUTRAL if
    exactly zero. UNAVAILABLE if fewer than `window` rows exist as of
    `as_of`, or any of those rows has an incomplete (None) net figure."""
    return _net_buying_signal("FOREIGN_NET_BUYING", "外資買超", flows, "foreign_net", as_of, window)


def investment_trust_net_buying_signal(flows: Sequence[_HasDateTrustNet], as_of: date_, window: int = 5) -> Signal:
    """Same as foreign_net_buying_signal but for 投信 (investment trust)."""
    return _net_buying_signal("INVESTMENT_TRUST_NET_BUYING", "投信買超", flows, "investment_trust_net", as_of, window)


def revenue_growth_positive_signal(fundamentals: Sequence[_HasPeriodRevenue], as_of: date_) -> Signal:
    """BULLISH if the latest YoY revenue growth is positive, BEARISH if
    negative, NEUTRAL if exactly zero. UNAVAILABLE if fewer than two
    revenue periods are known (see fundamentals_growth.revenue_growth_yoy).
    Known limitation: FundamentalsDTO has no announcement-date column, so
    this can't be strictly `as_of`-filtered the way price/flow signals are
    -- it reads whichever fundamentals rows the caller passes in (same
    limitation scoring_service.py's growth_score already has)."""
    growth = revenue_growth_yoy(list(fundamentals))
    if growth is None:
        return Signal("REVENUE_GROWTH_POSITIVE", "FUNDAMENTAL", "營收年增率", UNAVAILABLE, None, ZERO, as_of, "營收期數不足", "CALCULATED")

    if growth > ZERO:
        status, explanation = BULLISH, f"最新營收年增率 {growth * 100:.1f}% 為正"
    elif growth < ZERO:
        status, explanation = BEARISH, f"最新營收年增率 {growth * 100:.1f}% 為負"
    else:
        status, explanation = NEUTRAL, "最新營收年增率為零"
    return Signal("REVENUE_GROWTH_POSITIVE", "FUNDAMENTAL", "營收年增率", status, growth, ZERO, as_of, explanation, "CALCULATED")


def revenue_growth_accelerating_signal(fundamentals: Sequence[_HasPeriodRevenue], as_of: date_) -> Signal:
    """BULLISH if YoY revenue growth accelerated from the prior period to
    the latest one, BEARISH if it decelerated, NEUTRAL if unchanged.
    UNAVAILABLE unless both of the last two growth figures are known
    (needs 3 valid revenue periods). Same as-of limitation as
    revenue_growth_positive_signal above."""
    series = revenue_growth_series(list(fundamentals))
    if len(series) < 2 or series[-1] is None or series[-2] is None:
        return Signal(
            "REVENUE_GROWTH_ACCELERATING", "FUNDAMENTAL", "營收成長加速", UNAVAILABLE, None, ZERO, as_of, "營收期數不足", "CALCULATED"
        )

    latest, previous = series[-1], series[-2]
    delta = latest - previous
    if delta > ZERO:
        status, explanation = BULLISH, f"營收年增率由 {previous * 100:.1f}% 加速至 {latest * 100:.1f}%"
    elif delta < ZERO:
        status, explanation = BEARISH, f"營收年增率由 {previous * 100:.1f}% 減速至 {latest * 100:.1f}%"
    else:
        status, explanation = NEUTRAL, "營收年增率與前期持平"
    return Signal("REVENUE_GROWTH_ACCELERATING", "FUNDAMENTAL", "營收成長加速", status, delta, ZERO, as_of, explanation, "CALCULATED")


def composite_score_signal(
    composite_score: Decimal | None,
    as_of: date_,
    bullish: Decimal = Decimal(60),
    bearish: Decimal = Decimal(40),
) -> Signal:
    """BULLISH if the persisted composite score (app.analytics.scoring) is
    >= `bullish`, BEARISH if <= `bearish`, NEUTRAL in between. UNAVAILABLE
    if no score has been computed/persisted for this date. Reads the
    already-persisted score -- never recomputes it (spec Sec.18). V1
    thresholds, same "not empirically validated yet" caveat as the rest of
    scoring.py."""
    if composite_score is None:
        return Signal("COMPOSITE_SCORE", "COMPOSITE", "綜合評分", UNAVAILABLE, None, bullish, as_of, "尚無綜合評分", "CALCULATED")

    if composite_score >= bullish:
        status, explanation = BULLISH, f"綜合評分 {composite_score:.1f} 達 {bullish} 以上"
    elif composite_score <= bearish:
        status, explanation = BEARISH, f"綜合評分 {composite_score:.1f} 低於 {bearish} 以下"
    else:
        status, explanation = NEUTRAL, f"綜合評分 {composite_score:.1f} 落於中性區間"
    return Signal("COMPOSITE_SCORE", "COMPOSITE", "綜合評分", status, composite_score, bullish, as_of, explanation, "CALCULATED")


def overall_status(signals: Sequence[Signal]) -> str:
    """Unweighted majority vote (V1, documented -- not IC/backtest-weighted)
    over every non-UNAVAILABLE signal's status: whichever of BULLISH/
    BEARISH has more votes wins; a tie (including 0-0, i.e. every signal
    NEUTRAL) is NEUTRAL. UNAVAILABLE only if every signal is UNAVAILABLE."""
    counts = Counter(s.status for s in signals if s.status != UNAVAILABLE)
    if not counts:
        return UNAVAILABLE
    bullish_votes = counts.get(BULLISH, 0)
    bearish_votes = counts.get(BEARISH, 0)
    if bullish_votes > bearish_votes:
        return BULLISH
    if bearish_votes > bullish_votes:
        return BEARISH
    return NEUTRAL
