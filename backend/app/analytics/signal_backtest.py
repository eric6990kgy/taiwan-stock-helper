"""Walk-forward hit-rate backtest for a signal rule set (Phase 8). Ports
the concept behind 看盤台's own client-side `computeBacktest()` (replay
price history day-by-day, recompute what the signal would have said using
only data available that day, then check whether price actually moved
that direction `horizon` trading days later) -- reimplemented in Python
against this repo's own deterministic signal engine and Decimal price
history, not copied from 看盤台's JS or its specific indicator set.

Pure function: no DB/HTTP/FastAPI imports, same independence rule as the
rest of app.analytics. Used by StrategyService to attach a hit-rate to
both an active strategy version and a pending change's before/after
comparison.
"""

from dataclasses import dataclass
from datetime import date as date_
from decimal import Decimal
from typing import Protocol, Sequence

from app.analytics.signal_rules import SignalRules
from app.analytics.signals import overall_status, price_above_sma_signal, rsi_bullish_signal

WARMUP_DAYS = 60
DEFAULT_HORIZON = 5
DEFAULT_DEADZONE_PCT = Decimal("1")


class _HasDateClose(Protocol):
    date: date_
    close: Decimal


@dataclass(frozen=True)
class BacktestResult:
    hits: int
    n: int
    horizon: int
    deadzone_pct: Decimal

    @property
    def hit_rate(self) -> Decimal | None:
        """None (never a fabricated percentage) when there aren't enough
        non-neutral calls to make a rate meaningful -- same "sample too
        small, say so" convention as everywhere else in this codebase."""
        return None if self.n == 0 else Decimal(self.hits) / Decimal(self.n)


def _classify_direction(from_close: Decimal, to_close: Decimal, deadzone_pct: Decimal) -> str:
    change_pct = (to_close - from_close) / from_close * Decimal(100)
    if change_pct > deadzone_pct:
        return "BULLISH"
    if change_pct < -deadzone_pct:
        return "BEARISH"
    return "NEUTRAL"


def walk_forward_hit_rate(
    points: Sequence[_HasDateClose],
    rules: SignalRules,
    horizon: int = DEFAULT_HORIZON,
    deadzone_pct: Decimal = DEFAULT_DEADZONE_PCT,
) -> BacktestResult:
    """Only technical signals (SMA/RSI) are evaluated here -- institutional/
    fundamental/composite signals depend on data this function isn't given
    (flows, fundamentals, persisted scores) and are out of scope for a
    price-only walk-forward check. `points` must be sorted ascending by
    date and span real price history; the first `WARMUP_DAYS` are skipped
    (not enough history for a meaningful SMA/RSI read yet), and the last
    `horizon` days are skipped (no future close to check against yet)."""
    points = list(points)
    n = len(points)
    hits = 0
    calls = 0

    for i in range(WARMUP_DAYS, n - horizon):
        window = points[: i + 1]
        as_of = window[-1].date
        signals = [
            price_above_sma_signal(window, rules.sma_short, as_of),
            price_above_sma_signal(window, rules.sma_long, as_of),
            rsi_bullish_signal(window, as_of, rules.rsi_period),
        ]
        status = overall_status(signals)
        if status == "UNAVAILABLE" or status == "NEUTRAL":
            continue

        actual = _classify_direction(points[i].close, points[i + horizon].close, deadzone_pct)
        calls += 1
        if status == actual:
            hits += 1

    return BacktestResult(hits=hits, n=calls, horizon=horizon, deadzone_pct=deadzone_pct)
