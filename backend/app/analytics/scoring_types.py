"""Plain result structures for app/analytics/scoring.py. No ORM, no
Pydantic -- same independence rule as the rest of app/analytics.
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class SubScores:
    """Each field is None when that sub-score couldn't be computed
    (insufficient input data), never a fabricated neutral value."""

    value: Decimal | None
    growth: Decimal | None
    momentum: Decimal | None
    quality: Decimal | None


@dataclass(frozen=True)
class CompositeScoreResult:
    composite: Decimal | None
    sub_scores: SubScores
    regime: str | None
    # Sorted names of sub-scores that came back None, e.g. ["growth", "quality"].
    missing_components: list[str]
