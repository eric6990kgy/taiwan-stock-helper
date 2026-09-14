"""Historical portfolio equity-curve reconstruction and drawdown analysis
(個股訊號引擎規格書 Phase A — the -15%/-25% drawdown circuit breaker
confirmed with the user 2026-09-14).

The README's "Not built yet" list says historical time-series performance
doesn't exist -- this module deliberately does NOT try to build a general
performance-over-time feature. It reconstructs equity retroactively from
data that's already there (transactions + price_history), scoped tightly
to what the drawdown check and the benchmark/alpha comparison need. No new
daily-snapshot job is required to start using it.

Pure: no FastAPI/SQLAlchemy import (same rule as cost_basis.py/portfolio.py).
Callers fetch transactions + price history from the DB and pass plain data
in; see AnalyticsService.get_drawdown() for the assembly.
"""

from dataclasses import dataclass
from datetime import date as date_, timedelta
from decimal import Decimal

from app.analytics.cost_basis import calculate_positions
from app.analytics.types import Position, TransactionInput

DRAWDOWN_OK = "OK"
DRAWDOWN_PAUSE = "PAUSE_NEW_POSITIONS"
DRAWDOWN_STOP = "HARD_STOP"


@dataclass(frozen=True)
class EquityPoint:
    as_of: date_
    equity: Decimal


@dataclass(frozen=True)
class DrawdownStatus:
    as_of: date_
    equity: Decimal
    peak_equity: Decimal
    peak_date: date_
    drawdown_pct: Decimal  # <= 0; -0.18 means 18% off the running peak
    action: str  # DRAWDOWN_OK | DRAWDOWN_PAUSE | DRAWDOWN_STOP


def _value_positions(positions: dict[tuple, Position], last_close: dict[int, Decimal]) -> Decimal:
    total = Decimal("0")
    for (_, asset_id), position in positions.items():
        if position.remaining_shares == 0:
            continue
        price = last_close.get(asset_id)
        if price is None:
            continue  # no price known as of this day yet -- excluded, never zeroed
        total += position.remaining_shares * price
    return total


def build_equity_curve(
    transactions: list[TransactionInput],
    price_history: dict[int, list[tuple[date_, Decimal]]],
    start: date_,
    end: date_,
) -> list[EquityPoint]:
    """One point per calendar day from start to end (inclusive). Each day's
    equity replays only the transactions dated on or before that day
    (via the same calculate_positions() the rest of the app uses — no
    parallel position-math implementation) and values the result using the
    last known close on or before that day for each held asset.

    price_history: asset_id -> [(date, close), ...] sorted ascending, and
    should include rows *before* `start` too — a position opened before the
    window still needs its last pre-window close to be valued correctly on
    day `start`, not excluded for lack of a price.

    O(days * assets) via the cursor sweep below. Fine for a single-user,
    small-watchlist app; would need a smarter approach at real scale.
    """
    if start > end:
        raise ValueError("start must be <= end")

    sorted_txns = sorted(transactions, key=lambda t: (t.date, t.id))
    price_cursors = {asset_id: 0 for asset_id in price_history}
    last_close: dict[int, Decimal] = {}

    curve: list[EquityPoint] = []
    txn_idx = 0
    day = start
    while day <= end:
        while txn_idx < len(sorted_txns) and sorted_txns[txn_idx].date <= day:
            txn_idx += 1
        day_txns = sorted_txns[:txn_idx]

        for asset_id, rows in price_history.items():
            cursor = price_cursors[asset_id]
            while cursor < len(rows) and rows[cursor][0] <= day:
                last_close[asset_id] = rows[cursor][1]
                cursor += 1
            price_cursors[asset_id] = cursor

        positions = calculate_positions(day_txns) if day_txns else {}
        curve.append(EquityPoint(as_of=day, equity=_value_positions(positions, last_close)))
        day += timedelta(days=1)

    return curve


def evaluate_drawdown(curve: list[EquityPoint], pause_pct: Decimal, stop_pct: Decimal) -> DrawdownStatus | None:
    """Reports drawdown as of the LAST point of the curve only ("today's"
    status against the running peak seen anywhere in the curve) — not a
    day-by-day history of when triggers fired. Returns None for an empty
    curve (nothing to evaluate, e.g. no transactions yet)."""
    if not curve:
        return None

    peak_equity = curve[0].equity
    peak_date = curve[0].as_of
    for point in curve:
        if point.equity > peak_equity:
            peak_equity = point.equity
            peak_date = point.as_of

    latest = curve[-1]
    drawdown_pct = (latest.equity - peak_equity) / peak_equity if peak_equity != 0 else Decimal("0")

    if drawdown_pct <= -stop_pct:
        action = DRAWDOWN_STOP
    elif drawdown_pct <= -pause_pct:
        action = DRAWDOWN_PAUSE
    else:
        action = DRAWDOWN_OK

    return DrawdownStatus(
        as_of=latest.as_of,
        equity=latest.equity,
        peak_equity=peak_equity,
        peak_date=peak_date,
        drawdown_pct=drawdown_pct,
        action=action,
    )
