"""Hand-computed tests for app/analytics/scoring.py -- each sub-score
function, regime detection, and None-aware composite weighting."""

from decimal import Decimal

from app.analytics import scoring
from app.analytics.scoring_types import SubScores


def D(x) -> Decimal:
    return Decimal(str(x))


# ---- value_score --------------------------------------------------------------


def test_value_score_low_pe_low_pb_is_100():
    assert scoring.value_score(D(10), D(1)) == D(100)


def test_value_score_high_pe_high_pb_is_low():
    assert scoring.value_score(D(60), D(8)) == D(0)


def test_value_score_averages_pe_and_pb_when_both_present():
    pe = scoring.value_score(D(22.5), None)
    pb = scoring.value_score(None, D(2.25))
    both = scoring.value_score(D(22.5), D(2.25))
    assert both == (pe + pb) / 2


def test_value_score_none_when_both_missing():
    assert scoring.value_score(None, None) is None


def test_value_score_ignores_non_positive_ratios_instead_of_scoring_zero():
    """Negative/zero PE (e.g. negative earnings) isn't a real valuation
    signal -- excluded from the average, not treated as a bad score."""
    assert scoring.value_score(D(-5), D(2)) == scoring.value_score(None, D(2))
    assert scoring.value_score(D(0), None) is None


# ---- growth_score ---------------------------------------------------------------


def test_growth_score_none_when_input_missing():
    assert scoring.growth_score(None) is None


def test_growth_score_hand_computed_points():
    assert scoring.growth_score(D(-20)) == D(0)
    assert scoring.growth_score(D(0)) == D(40)
    assert scoring.growth_score(D(20)) == D(80)
    assert scoring.growth_score(D(50)) == D(100)


def test_growth_score_clamps_extremes():
    assert scoring.growth_score(D(-99)) == D(0)
    assert scoring.growth_score(D(200)) == D(100)


def test_growth_score_interpolates_between_breakpoints():
    assert scoring.growth_score(D(10)) == D(60)  # midpoint of 0->20 segment (40->80)


# ---- momentum_score ---------------------------------------------------------------


def test_momentum_score_none_when_all_inputs_missing():
    assert scoring.momentum_score(None, None, None, None) is None


def test_momentum_score_rsi_peaks_at_sixty():
    assert scoring.momentum_score(D(60), None, None, None) == D(100)
    assert scoring.momentum_score(D(30), None, None, None) == D(40)
    assert scoring.momentum_score(D(90), None, None, None) == D(40)


def test_momentum_score_sma_component_is_binary():
    assert scoring.momentum_score(None, D(110), D(100), None) == D(100)  # above SMA
    assert scoring.momentum_score(None, D(90), D(100), None) == D(0)  # below SMA


def test_momentum_score_macd_component_sign():
    assert scoring.momentum_score(None, None, None, D(5)) == D(100)
    assert scoring.momentum_score(None, None, None, D(-5)) == D(0)
    assert scoring.momentum_score(None, None, None, D(0)) == D(50)


def test_momentum_score_averages_available_components():
    rsi_only = scoring.momentum_score(D(60), None, None, None)
    macd_only = scoring.momentum_score(None, None, None, D(5))
    both = scoring.momentum_score(D(60), None, None, D(5))
    assert both == (rsi_only + macd_only) / 2


# ---- quality_score ---------------------------------------------------------------


def test_quality_score_none_when_all_inputs_missing():
    assert scoring.quality_score(None, None, None) is None


def test_quality_score_hand_computed_roe_component():
    # roe=0.25 (25%) -> full ROE component (100), isolated via no other inputs.
    assert scoring.quality_score(D("0.25"), None, None) == D(100)
    assert scoring.quality_score(D("0"), None, None) == D(0)
    assert scoring.quality_score(D("0.125"), None, None) == D(50)  # midpoint


def test_quality_score_debt_ratio_lower_is_better():
    assert scoring.quality_score(None, D("0.3"), None) == D(100)
    assert scoring.quality_score(None, D("0.7"), None) == D(0)
    assert scoring.quality_score(None, D("1.0"), None) == D(0)  # clamped past the high end


def test_quality_score_dividend_yield_uses_percentage_scale_not_fraction():
    """dividend_yield comes in already percentage-scale (FinMind's own
    convention, e.g. 0.91 meaning 0.91%) -- distinct from roe/debt_ratio's
    fraction scale (e.g. 0.18 meaning 18%)."""
    assert scoring.quality_score(None, None, D("5")) == D(100)
    assert scoring.quality_score(None, None, D("0")) == D(0)
    assert scoring.quality_score(None, None, D("2.5")) == D(50)


def test_quality_score_averages_available_components():
    roe_only = scoring.quality_score(D("0.25"), None, None)
    debt_only = scoring.quality_score(None, D("0.3"), None)
    both = scoring.quality_score(D("0.25"), D("0.3"), None)
    assert both == (roe_only + debt_only) / 2


# ---- detect_regime ---------------------------------------------------------------


def test_detect_regime_none_below_200_observations():
    closes = [D(100 + i) for i in range(199)]
    assert scoring.detect_regime(closes) is None


def test_detect_regime_bull_when_uptrend():
    closes = [D(100 + i) for i in range(200)]  # steadily rising
    assert scoring.detect_regime(closes) == "BULL"


def test_detect_regime_bear_when_downtrend():
    closes = [D(300 - i) for i in range(200)]  # steadily falling
    assert scoring.detect_regime(closes) == "BEAR"


def test_detect_regime_neutral_when_choppy():
    # Oscillates around a flat level -- neither a clean uptrend nor downtrend.
    closes = [D(100 + (5 if i % 2 == 0 else -5)) for i in range(200)]
    assert scoring.detect_regime(closes) == "NEUTRAL"


def test_detect_regime_empty_input():
    assert scoring.detect_regime([]) is None


# ---- composite_score: None-aware weighting ---------------------------------------


def test_composite_score_all_present_uses_regime_weights():
    sub = SubScores(value=D(80), growth=D(70), momentum=D(90), quality=D(60))
    result = scoring.composite_score(sub, "BULL")
    weights = scoring.REGIME_WEIGHTS["BULL"]
    expected = D(80) * weights["value"] + D(70) * weights["growth"] + D(90) * weights["momentum"] + D(60) * weights["quality"]
    assert result.composite == expected
    assert result.missing_components == []
    assert result.regime == "BULL"


def test_composite_score_renormalizes_when_some_missing():
    sub = SubScores(value=D(80), growth=None, momentum=None, quality=D(60))
    result = scoring.composite_score(sub, "NEUTRAL")
    # Equal weights in NEUTRAL -> missing ones drop out, remaining two average evenly.
    assert result.composite == (D(80) + D(60)) / 2
    assert result.missing_components == ["growth", "momentum"]


def test_composite_score_none_when_everything_missing():
    sub = SubScores(value=None, growth=None, momentum=None, quality=None)
    result = scoring.composite_score(sub, "BEAR")
    assert result.composite is None
    assert sorted(result.missing_components) == ["growth", "momentum", "quality", "value"]


def test_composite_score_unknown_regime_falls_back_to_neutral_weights():
    sub = SubScores(value=D(100), growth=D(100), momentum=D(100), quality=D(100))
    result = scoring.composite_score(sub, None)
    assert result.composite == D(100)
    result_unknown = scoring.composite_score(sub, "SOMETHING_ELSE")
    assert result_unknown.composite == D(100)
