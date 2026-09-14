from decimal import Decimal

from app.analytics.benchmark import calculate_alpha, period_return


def test_period_return_basic():
    assert period_return(Decimal("100"), Decimal("110")) == Decimal("0.10")


def test_period_return_negative():
    assert period_return(Decimal("100"), Decimal("90")) == Decimal("-0.10")


def test_period_return_none_when_start_is_zero():
    assert period_return(Decimal("0"), Decimal("110")) is None


def test_period_return_none_when_either_side_missing():
    assert period_return(None, Decimal("110")) is None
    assert period_return(Decimal("100"), None) is None


def test_calculate_alpha_positive_when_portfolio_beats_benchmark():
    assert calculate_alpha(Decimal("0.15"), Decimal("0.05")) == Decimal("0.10")


def test_calculate_alpha_negative_when_portfolio_trails_benchmark():
    assert calculate_alpha(Decimal("0.02"), Decimal("0.05")) == Decimal("-0.03")


def test_calculate_alpha_none_propagates():
    assert calculate_alpha(None, Decimal("0.05")) is None
    assert calculate_alpha(Decimal("0.05"), None) is None
