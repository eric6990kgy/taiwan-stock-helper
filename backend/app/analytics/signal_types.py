"""Plain result structures for app/analytics/signals.py. No ORM, no
Pydantic -- same independence rule as the rest of app/analytics.
"""

from dataclasses import dataclass
from datetime import date as date_
from decimal import Decimal

BULLISH = "BULLISH"
BEARISH = "BEARISH"
NEUTRAL = "NEUTRAL"
UNAVAILABLE = "UNAVAILABLE"

SignalStatus = str  # one of BULLISH | BEARISH | NEUTRAL | UNAVAILABLE


@dataclass(frozen=True)
class Signal:
    """One discrete BULLISH/BEARISH/NEUTRAL/UNAVAILABLE reading. `value` and
    `threshold` are whatever raw numbers explain the status (e.g. the close
    and the SMA it's compared against) -- None when the signal itself is
    UNAVAILABLE. Never carries BUY/SELL vocabulary (spec Sec.7)."""

    id: str
    category: str  # "TECHNICAL" | "INSTITUTIONAL" | "FUNDAMENTAL" | "COMPOSITE"
    name: str
    status: SignalStatus
    value: Decimal | None
    threshold: Decimal | None
    as_of: date_ | None
    explanation: str
    source: str


@dataclass(frozen=True)
class SignalResult:
    ticker: str
    as_of: date_ | None
    signals: list[Signal]
    overall_status: SignalStatus
    composite_score: Decimal | None
    regime: str | None
