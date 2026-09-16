"""Tests for app/analytics/fundamentals_growth.py -- revenue_growth_series()
(new, Phase 7 Part 2) and a regression check that revenue_growth_yoy()'s
behavior is unchanged after being refactored to reuse it."""

from dataclasses import dataclass
from decimal import Decimal

from app.analytics.fundamentals_growth import revenue_growth_series, revenue_growth_yoy


@dataclass
class Fund:
    period: str
    revenue: Decimal | None


def test_revenue_growth_series_first_entry_is_always_none():
    series = revenue_growth_series([Fund("2026Q1", Decimal("100"))])
    assert series == [None]


def test_revenue_growth_series_computes_each_consecutive_pair():
    funds = [Fund("2024Q4", Decimal("100")), Fund("2025Q4", Decimal("110")), Fund("2026Q4", Decimal("121"))]
    series = revenue_growth_series(funds)
    assert series == [None, Decimal("0.1"), Decimal("0.1")]


def test_revenue_growth_series_sorts_by_period_regardless_of_input_order():
    funds = [Fund("2026Q4", Decimal("121")), Fund("2024Q4", Decimal("100")), Fund("2025Q4", Decimal("110"))]
    series = revenue_growth_series(funds)
    assert series == [None, Decimal("0.1"), Decimal("0.1")]


def test_revenue_growth_series_skips_rows_with_none_revenue():
    funds = [Fund("2024Q4", Decimal("100")), Fund("2025Q4", None), Fund("2026Q4", Decimal("110"))]
    series = revenue_growth_series(funds)
    assert series == [None, Decimal("0.1")]


def test_revenue_growth_series_none_when_prior_period_revenue_is_zero():
    funds = [Fund("2024Q4", Decimal("0")), Fund("2025Q4", Decimal("100"))]
    series = revenue_growth_series(funds)
    assert series == [None, None]


def test_revenue_growth_series_empty_input_is_empty_output():
    assert revenue_growth_series([]) == []


# ---- revenue_growth_yoy regression (post-refactor to reuse the series) ----


def test_revenue_growth_yoy_matches_last_series_entry():
    funds = [Fund("2024Q4", Decimal("100")), Fund("2025Q4", Decimal("110")), Fund("2026Q4", Decimal("121"))]
    assert revenue_growth_yoy(funds) == revenue_growth_series(funds)[-1] == Decimal("0.1")


def test_revenue_growth_yoy_none_with_fewer_than_two_periods():
    assert revenue_growth_yoy([Fund("2026Q4", Decimal("100"))]) is None
    assert revenue_growth_yoy([]) is None


def test_revenue_growth_yoy_none_when_prior_period_revenue_is_zero():
    funds = [Fund("2024Q4", Decimal("0")), Fund("2025Q4", Decimal("100"))]
    assert revenue_growth_yoy(funds) is None


def test_revenue_growth_yoy_ignores_rows_with_none_revenue():
    funds = [Fund("2024Q4", Decimal("100")), Fund("2025Q4", None), Fund("2026Q4", Decimal("150"))]
    assert revenue_growth_yoy(funds) == Decimal("0.5")
