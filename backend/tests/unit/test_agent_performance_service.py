"""AgentPerformanceService tests (Phase 12) -- the per-role KPI reuses
Phase 10's already-scored RecommendationOutcome rows entirely (no new
scoring pass): seeds a Recommendation + RecommendationOutcome + a couple
of AgentAnalysis rows directly, same "seed real DB rows by hand" approach
as test_recommendation_outcome_service.py.
"""

from datetime import date, timedelta
from decimal import Decimal

from app.models.agent_analysis import AgentAnalysis
from app.models.asset import Asset
from app.models.recommendation import Recommendation
from app.models.recommendation_outcome import RecommendationOutcome
from app.services.agent_performance_service import AgentPerformanceService
from app.services.strategy_service import StrategyService

D0 = date(2026, 1, 1)


def make_recommendation_with_outcome(db, actual_direction="BULLISH") -> Recommendation:
    asset = Asset(ticker="2330", name="Test Co", asset_type="STOCK", currency="TWD", is_demo_data=False)
    db.add(asset)
    db.flush()
    strategy_version_id = StrategyService(db).get_active_version().id
    rec = Recommendation(
        asset_id=asset.id,
        strategy_version_id=strategy_version_id,
        action="CONSIDER_INCREASE",
        previous_status="NEUTRAL",
        new_status="BULLISH",
        triggered_signals=[],
        risk_blocked=False,
        as_of_date=D0,
    )
    db.add(rec)
    db.flush()
    outcome = RecommendationOutcome(
        recommendation_id=rec.id,
        horizon_trading_days=5,
        as_of_date=D0,
        outcome_date=D0 + timedelta(days=5),
        from_close=Decimal("100"),
        to_close=Decimal("110"),
        actual_direction=actual_direction,
        hit=True,
    )
    db.add(outcome)
    db.flush()
    return rec


def add_analysis(db, recommendation_id, role, call, confidence=70) -> AgentAnalysis:
    row = AgentAnalysis(
        recommendation_id=recommendation_id, role=role, call=call, confidence=confidence, details={"key_risk": "x"},
        model="gemini-3.8-flash",
    )
    db.add(row)
    db.flush()
    return row


def test_hit_rate_is_null_with_no_scored_analyses(db_session):
    summary = AgentPerformanceService(db_session).get_summary()
    assert summary.n == 0
    assert summary.hit_rate is None


def test_call_matching_actual_direction_is_a_hit(db_session):
    rec = make_recommendation_with_outcome(db_session, actual_direction="BULLISH")
    add_analysis(db_session, rec.id, "FUNDAMENTAL_ANALYST", "BULLISH")

    summary = AgentPerformanceService(db_session).get_summary()

    assert summary.n == 1
    assert summary.hits == 1
    assert summary.hit_rate == Decimal("1")


def test_call_not_matching_actual_direction_is_a_miss(db_session):
    rec = make_recommendation_with_outcome(db_session, actual_direction="BEARISH")
    add_analysis(db_session, rec.id, "FUNDAMENTAL_ANALYST", "BULLISH")

    summary = AgentPerformanceService(db_session).get_summary()

    assert summary.n == 1
    assert summary.hits == 0


def test_unavailable_calls_are_excluded_from_the_denominator(db_session):
    rec = make_recommendation_with_outcome(db_session, actual_direction="BULLISH")
    add_analysis(db_session, rec.id, "TECHNICAL_ANALYST", "UNAVAILABLE")

    summary = AgentPerformanceService(db_session).get_summary()

    assert summary.n == 0
    assert summary.hit_rate is None


def test_role_filter_separates_roles(db_session):
    rec = make_recommendation_with_outcome(db_session, actual_direction="BULLISH")
    add_analysis(db_session, rec.id, "FUNDAMENTAL_ANALYST", "BULLISH")
    add_analysis(db_session, rec.id, "TECHNICAL_ANALYST", "BEARISH")

    service = AgentPerformanceService(db_session)
    fundamental_summary = service.get_summary(role="FUNDAMENTAL_ANALYST")
    technical_summary = service.get_summary(role="TECHNICAL_ANALYST")

    assert fundamental_summary.n == 1
    assert fundamental_summary.hits == 1
    assert technical_summary.n == 1
    assert technical_summary.hits == 0


def test_analysis_without_a_scored_outcome_yet_is_not_counted(db_session):
    asset = Asset(ticker="2330", name="Test Co", asset_type="STOCK", currency="TWD", is_demo_data=False)
    db_session.add(asset)
    db_session.flush()
    strategy_version_id = StrategyService(db_session).get_active_version().id
    rec = Recommendation(
        asset_id=asset.id,
        strategy_version_id=strategy_version_id,
        action="CONSIDER_INCREASE",
        previous_status="NEUTRAL",
        new_status="BULLISH",
        triggered_signals=[],
        risk_blocked=False,
    )
    db_session.add(rec)
    db_session.flush()
    add_analysis(db_session, rec.id, "FUNDAMENTAL_ANALYST", "BULLISH")

    summary = AgentPerformanceService(db_session).get_summary()

    assert summary.n == 0
