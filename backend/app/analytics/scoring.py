"""Pure, deterministic composite scoring (Phase 7). No ORM, no Pydantic, no
HTTP, no FastAPI -- same independence rule as the rest of app/analytics.

Design (per the External Project Integration Report's twstock-research
reference, reimplemented from its *pattern*, not its numbers):
  - Four style sub-scores (value/growth/momentum/quality), each 0-100 or
    None when its inputs are missing -- never a fabricated 50 "neutral".
  - A market-regime read (BULL/BEAR/NEUTRAL, from TAIEX's own SMA50/SMA200
    relationship) selects which weight table combines the sub-scores into
    one composite score.
  - The weighted mean is None-aware: a missing sub-score is dropped and the
    remaining weights renormalize, rather than treating it as 0. If every
    sub-score is missing, the composite is None too.

IMPORTANT: every threshold and weight below is a V1 placeholder, picked for
being simple and directionally sensible -- NOT validated against this
market's own return data (no IC/backtesting infrastructure exists yet, see
the Phase 6 report's Phase 9 recommendation). Treat this as a starting
point to validate empirically, not a tuned model, the same caution the
Integration Report raised about copying twstock-research's own weights.
"""

from decimal import Decimal
from typing import Sequence

from app.analytics import technical
from app.analytics.scoring_types import CompositeScoreResult, SubScores

ZERO = Decimal(0)
HUNDRED = Decimal(100)


def _clamp(value: Decimal, low: Decimal = ZERO, high: Decimal = HUNDRED) -> Decimal:
    return max(low, min(high, value))


def _lerp(x: Decimal, x0: Decimal, x1: Decimal, y0: Decimal, y1: Decimal) -> Decimal:
    """Linearly interpolate y for x in [x0, x1] -> [y0, y1]."""
    return y0 + (x - x0) * (y1 - y0) / (x1 - x0)


def _mean(values: Sequence[Decimal]) -> Decimal | None:
    values = [v for v in values if v is not None]
    if not values:
        return None
    return sum(values) / Decimal(len(values))


def _pe_component(pe_ratio: Decimal) -> Decimal:
    if pe_ratio <= Decimal(15):
        return HUNDRED
    if pe_ratio <= Decimal(30):
        return _lerp(pe_ratio, Decimal(15), Decimal(30), HUNDRED, Decimal(50))
    if pe_ratio <= Decimal(50):
        return _lerp(pe_ratio, Decimal(30), Decimal(50), Decimal(50), ZERO)
    return ZERO


def _pb_component(pb_ratio: Decimal) -> Decimal:
    if pb_ratio <= Decimal("1.5"):
        return HUNDRED
    if pb_ratio <= Decimal(3):
        return _lerp(pb_ratio, Decimal("1.5"), Decimal(3), HUNDRED, Decimal(50))
    if pb_ratio <= Decimal(6):
        return _lerp(pb_ratio, Decimal(3), Decimal(6), Decimal(50), ZERO)
    return ZERO


def value_score(pe_ratio: Decimal | None, pb_ratio: Decimal | None) -> Decimal | None:
    """Lower PE/PB -> higher score. A non-positive ratio (e.g. negative
    earnings) can't be meaningfully scored -- excluded, not scored as 0."""
    pe_component = _pe_component(pe_ratio) if pe_ratio is not None and pe_ratio > 0 else None
    pb_component = _pb_component(pb_ratio) if pb_ratio is not None and pb_ratio > 0 else None
    return _mean([pe_component, pb_component])


def growth_score(revenue_growth_pct: Decimal | None) -> Decimal | None:
    """revenue_growth_pct is a percentage (e.g. Decimal(15) for 15% YoY),
    matching ScreenerService's/ResearchService's existing convention."""
    if revenue_growth_pct is None:
        return None
    g = revenue_growth_pct
    if g <= Decimal(-20):
        return ZERO
    if g <= ZERO:
        return _lerp(g, Decimal(-20), ZERO, ZERO, Decimal(40))
    if g <= Decimal(20):
        return _lerp(g, ZERO, Decimal(20), Decimal(40), Decimal(80))
    if g <= Decimal(50):
        return _lerp(g, Decimal(20), Decimal(50), Decimal(80), HUNDRED)
    return HUNDRED


def momentum_score(
    rsi_14: Decimal | None,
    close: Decimal | None,
    sma_20: Decimal | None,
    macd_histogram: Decimal | None,
) -> Decimal | None:
    """Combines whichever of the three signals are available: RSI centered
    at 60 (a mild-bullish sweet spot, not overbought), close-vs-SMA20 sign,
    and MACD histogram sign."""
    rsi_component = _clamp(HUNDRED - abs(rsi_14 - Decimal(60)) * 2) if rsi_14 is not None else None

    sma_component = None
    if close is not None and sma_20 is not None:
        sma_component = HUNDRED if close > sma_20 else ZERO

    macd_component = None
    if macd_histogram is not None:
        if macd_histogram > ZERO:
            macd_component = HUNDRED
        elif macd_histogram < ZERO:
            macd_component = ZERO
        else:
            macd_component = Decimal(50)

    return _mean([rsi_component, sma_component, macd_component])


def quality_score(
    roe: Decimal | None,
    debt_ratio: Decimal | None,
    dividend_yield: Decimal | None,
) -> Decimal | None:
    """roe/debt_ratio are fractions (e.g. Decimal("0.18") for 18%), matching
    FundamentalsDTO's convention. dividend_yield is already percentage-scale
    (e.g. Decimal("0.91") meaning 0.91%), matching FinMind's own field and
    ValuationDTO's convention -- deliberately NOT the same scale as
    roe/debt_ratio, so each is converted explicitly below."""
    roe_component = None
    if roe is not None:
        roe_pct = roe * HUNDRED
        if roe_pct <= ZERO:
            roe_component = ZERO
        elif roe_pct <= Decimal(25):
            roe_component = _lerp(roe_pct, ZERO, Decimal(25), ZERO, HUNDRED)
        else:
            roe_component = HUNDRED

    debt_component = None
    if debt_ratio is not None:
        if debt_ratio <= Decimal("0.3"):
            debt_component = HUNDRED
        elif debt_ratio <= Decimal("0.7"):
            debt_component = _lerp(debt_ratio, Decimal("0.3"), Decimal("0.7"), HUNDRED, ZERO)
        else:
            debt_component = ZERO

    yield_component = None
    if dividend_yield is not None:
        if dividend_yield <= ZERO:
            yield_component = ZERO
        elif dividend_yield <= Decimal(5):
            yield_component = _lerp(dividend_yield, ZERO, Decimal(5), ZERO, HUNDRED)
        else:
            yield_component = HUNDRED

    return _mean([roe_component, debt_component, yield_component])


def detect_regime(taiex_closes: Sequence[Decimal]) -> str | None:
    """BULL: latest close and SMA50 both above SMA200 (uptrend). BEAR: both
    below. Otherwise NEUTRAL. None if there isn't enough history yet for
    SMA200 (the longest input this needs)."""
    if len(taiex_closes) < 200:
        return None
    sma50 = technical.sma(taiex_closes, 50)[-1]
    sma200 = technical.sma(taiex_closes, 200)[-1]
    if sma50 is None or sma200 is None:
        return None
    latest = taiex_closes[-1]
    if latest > sma200 and sma50 > sma200:
        return "BULL"
    if latest < sma200 and sma50 < sma200:
        return "BEAR"
    return "NEUTRAL"


# V1 placeholders (see module docstring) -- BULL tilts toward momentum,
# BEAR tilts toward value/quality, NEUTRAL (and an unknown/None regime) is
# equal-weighted.
REGIME_WEIGHTS: dict[str, dict[str, Decimal]] = {
    "BULL": {"value": Decimal("0.20"), "growth": Decimal("0.25"), "momentum": Decimal("0.35"), "quality": Decimal("0.20")},
    "BEAR": {"value": Decimal("0.30"), "growth": Decimal("0.20"), "momentum": Decimal("0.15"), "quality": Decimal("0.35")},
    "NEUTRAL": {"value": Decimal("0.25"), "growth": Decimal("0.25"), "momentum": Decimal("0.25"), "quality": Decimal("0.25")},
}
DEFAULT_WEIGHTS = REGIME_WEIGHTS["NEUTRAL"]


def composite_score(sub_scores: SubScores, regime: str | None) -> CompositeScoreResult:
    """None-aware weighted mean: a missing sub-score is dropped and the
    remaining weights renormalize over just the ones present. composite is
    None only when every sub-score is missing."""
    weights = REGIME_WEIGHTS.get(regime, DEFAULT_WEIGHTS)
    components = {
        "value": sub_scores.value,
        "growth": sub_scores.growth,
        "momentum": sub_scores.momentum,
        "quality": sub_scores.quality,
    }
    available = {name: value for name, value in components.items() if value is not None}
    missing = sorted(name for name, value in components.items() if value is None)

    if not available:
        return CompositeScoreResult(composite=None, sub_scores=sub_scores, regime=regime, missing_components=missing)

    total_weight = sum(weights[name] for name in available)
    weighted_sum = sum(value * weights[name] for name, value in available.items())
    return CompositeScoreResult(
        composite=weighted_sum / total_weight, sub_scores=sub_scores, regime=regime, missing_components=missing
    )
