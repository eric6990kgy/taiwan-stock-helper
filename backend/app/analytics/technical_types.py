"""Plain result structures for app/analytics/technical.py. No ORM, no
Pydantic, no provider DTOs -- keeps this package importable without
FastAPI/SQLAlchemy on the path, same rule as app/analytics/types.py.
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class MACDResult:
    """Index-aligned with the input closes list -- macd_line[i]/signal_line[i]/
    histogram[i] are all computed using only closes[0..i] (Sec.12: no
    look-ahead). None wherever there isn't enough history yet."""

    macd_line: list[Decimal | None]
    signal_line: list[Decimal | None]
    histogram: list[Decimal | None]


@dataclass(frozen=True)
class BollingerBandsResult:
    upper: list[Decimal | None]
    middle: list[Decimal | None]
    lower: list[Decimal | None]


@dataclass(frozen=True)
class KDResult:
    k: list[Decimal | None]
    d: list[Decimal | None]
