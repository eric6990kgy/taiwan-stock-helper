from decimal import Decimal

from app.analytics.risk_limits import POSITION, SECTOR, LimitViolation, check_limits


def test_no_violations_when_everything_under_limit():
    weights = {"2330": Decimal("0.10"), "2454": Decimal("0.05")}
    assert check_limits(weights, Decimal("0.15"), POSITION) == []


def test_flags_position_over_limit():
    weights = {"2330": Decimal("0.20"), "2454": Decimal("0.05")}
    violations = check_limits(weights, Decimal("0.15"), POSITION)
    assert violations == [LimitViolation(kind=POSITION, label="2330", weight=Decimal("0.20"), limit=Decimal("0.15"))]


def test_exactly_at_limit_is_not_a_violation():
    weights = {"2330": Decimal("0.15")}
    assert check_limits(weights, Decimal("0.15"), POSITION) == []


def test_sector_violations_sorted_worst_first():
    weights = {
        "半導體核心": Decimal("0.50"),
        "航運三雄": Decimal("0.35"),
        "食品": Decimal("0.10"),
    }
    violations = check_limits(weights, Decimal("0.30"), SECTOR)
    assert [v.label for v in violations] == ["半導體核心", "航運三雄"]


def test_none_weight_entries_are_skipped_not_compared():
    """An empty portfolio reports weight=None (calculate_portfolio_weight's
    convention) -- that must never be miscompared against a numeric limit."""
    weights = {"2330": None}
    assert check_limits(weights, Decimal("0.15"), POSITION) == []


def test_unlabeled_sector_gets_a_placeholder_label():
    weights = {None: Decimal("0.40")}
    violations = check_limits(weights, Decimal("0.30"), SECTOR)
    assert violations[0].label == "(未分類)"
