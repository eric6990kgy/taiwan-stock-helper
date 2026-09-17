"""RecommendationOutcomeService tests -- scoring past Recommendations
against ground truth (Phase 10). Seeds real DB rows directly (same
approach as test_recommendation_service.py), constructing Recommendation
rows by hand for full control over as_of_date/new_status rather than
going through a live run_daily_scan() cycle.
"""

from datetime import date, timedelta
from decimal import Decimal

from app.models.asset import Asset
from app.models.recommendation import Recommendation
from app.repositories.price_repository import PriceRepository
from app.services.recommendation_outcome_service import RecommendationOutcomeService
from app.services.strategy_service import StrategyService

D0 = date(2026, 1, 1)


def make_asset(db, ticker="2330") -> Asset:
    asset = Asset(ticker=ticker, name="Test Co", asset_type="STOCK", currency="TWD", is_demo_data=False)
    db.add(asset)
    db.flush()
    return asset


def seed_prices(db, asset, closes: list[str], start: date = D0) -> None:
    prices = PriceRepository(db)
    for i, close in enumerate(closes):
        prices.upsert(asset.id, start + timedelta(days=i), close=Decimal(close), source="TEST")


def make_recommendation(db, asset, new_status="BULLISH", action="CONSIDER_INCREASE", as_of_date=None, created_at=None) -> Recommendation:
    strategy_version_id = StrategyService(db).get_active_version().id
    rec = Recommendation(
        asset_id=asset.id,
        strategy_version_id=strategy_version_id,
        action=action,
        previous_status="NEUTRAL",
        new_status=new_status,
        triggered_signals=[],
        risk_blocked=False,
        as_of_date=as_of_date,
    )
    db.add(rec)
    db.flush()
    if created_at is not None:
        rec.created_at = created_at
        db.flush()
    return rec


def test_bullish_call_that_rose_is_scored_a_hit(db_session):
    asset = make_asset(db_session)
    # 10 days of price history: close rises every day past the deadzone.
    seed_prices(db_session, asset, [str(100 + i) for i in range(10)])
    rec = make_recommendation(db_session, asset, new_status="BULLISH", as_of_date=D0)

    scored = RecommendationOutcomeService(db_session, horizon=5).score_due_outcomes()

    assert len(scored) == 1
    assert scored[0].recommendation_id == rec.id
    assert scored[0].actual_direction == "BULLISH"
    assert scored[0].hit is True
    assert scored[0].from_close == Decimal("100.0000")
    assert scored[0].to_close == Decimal("105.0000")
    assert scored[0].outcome_date == D0 + timedelta(days=5)


def test_bullish_call_that_fell_is_scored_a_miss(db_session):
    asset = make_asset(db_session)
    seed_prices(db_session, asset, [str(100 - i) for i in range(10)])
    make_recommendation(db_session, asset, new_status="BULLISH", as_of_date=D0)

    scored = RecommendationOutcomeService(db_session, horizon=5).score_due_outcomes()

    assert scored[0].actual_direction == "BEARISH"
    assert scored[0].hit is False


def test_bearish_call_that_fell_is_scored_a_hit(db_session):
    asset = make_asset(db_session)
    seed_prices(db_session, asset, [str(100 - i) for i in range(10)])
    make_recommendation(db_session, asset, new_status="BEARISH", action="CONSIDER_DECREASE", as_of_date=D0)

    scored = RecommendationOutcomeService(db_session, horizon=5).score_due_outcomes()

    assert scored[0].hit is True


def test_recommendation_not_yet_at_horizon_is_skipped_not_null(db_session):
    """Only 3 days of future price history exist -- horizon=5 hasn't
    elapsed yet. No RecommendationOutcome row should be created at all
    (absence of a row means "not due", never a fabricated placeholder)."""
    asset = make_asset(db_session)
    seed_prices(db_session, asset, [str(100 + i) for i in range(4)])  # only D0..D0+3
    make_recommendation(db_session, asset, new_status="BULLISH", as_of_date=D0)

    scored = RecommendationOutcomeService(db_session, horizon=5).score_due_outcomes()

    assert scored == []


def test_watch_recommendations_are_never_scored(db_session):
    asset = make_asset(db_session)
    seed_prices(db_session, asset, [str(100 + i) for i in range(10)])
    make_recommendation(db_session, asset, new_status="NEUTRAL", action="WATCH", as_of_date=D0)

    scored = RecommendationOutcomeService(db_session, horizon=5).score_due_outcomes()

    assert scored == []


def test_legacy_row_with_null_as_of_date_falls_back_to_nearest_price_at_or_before_created_at(db_session):
    asset = make_asset(db_session)
    seed_prices(db_session, asset, [str(100 + i) for i in range(10)])
    # created_at lands on D0+2 (a real trading date with a price row) --
    # as_of_date is left NULL, simulating a pre-Phase-10 recommendation.
    from datetime import datetime

    make_recommendation(db_session, asset, new_status="BULLISH", as_of_date=None, created_at=datetime(2026, 1, 3, 20, 0))

    scored = RecommendationOutcomeService(db_session, horizon=5).score_due_outcomes()

    assert len(scored) == 1
    assert scored[0].as_of_date == date(2026, 1, 3)
    assert scored[0].from_close == Decimal("102.0000")


def test_retroactive_batch_scores_multiple_old_past_due_recommendations_at_once(db_session):
    asset_a = make_asset(db_session, ticker="1111")
    asset_b = make_asset(db_session, ticker="2222")
    seed_prices(db_session, asset_a, [str(100 + i) for i in range(10)])
    seed_prices(db_session, asset_b, [str(200 - i) for i in range(10)])
    make_recommendation(db_session, asset_a, new_status="BULLISH", as_of_date=D0)
    make_recommendation(db_session, asset_b, new_status="BEARISH", action="CONSIDER_DECREASE", as_of_date=D0)

    scored = RecommendationOutcomeService(db_session, horizon=5).score_due_outcomes()

    assert len(scored) == 2
    assert all(o.hit for o in scored)

    # A second call is a no-op -- both are already scored.
    assert RecommendationOutcomeService(db_session, horizon=5).score_due_outcomes() == []


def test_review_summary_hit_rate_is_null_with_no_scored_sample(db_session):
    summary = RecommendationOutcomeService(db_session).get_review_summary()
    assert summary.n == 0
    assert summary.hit_rate is None


def test_review_summary_aggregates_hits_and_n_across_scored_outcomes(db_session):
    asset_a = make_asset(db_session, ticker="1111")
    asset_b = make_asset(db_session, ticker="2222")
    seed_prices(db_session, asset_a, [str(100 + i) for i in range(10)])  # rises -- BULLISH call hits
    seed_prices(db_session, asset_b, [str(200 + i) for i in range(10)])  # also rises -- BEARISH call misses
    make_recommendation(db_session, asset_a, new_status="BULLISH", as_of_date=D0)
    make_recommendation(db_session, asset_b, new_status="BEARISH", action="CONSIDER_DECREASE", as_of_date=D0)

    service = RecommendationOutcomeService(db_session, horizon=5)
    service.score_due_outcomes()
    summary = service.get_review_summary()

    assert summary.n == 2
    assert summary.hits == 1
    assert summary.hit_rate == Decimal("0.5")


def test_review_summary_action_filter_separates_increase_from_decrease(db_session):
    asset_a = make_asset(db_session, ticker="1111")
    asset_b = make_asset(db_session, ticker="2222")
    seed_prices(db_session, asset_a, [str(100 + i) for i in range(10)])
    seed_prices(db_session, asset_b, [str(200 - i) for i in range(10)])
    make_recommendation(db_session, asset_a, new_status="BULLISH", action="CONSIDER_INCREASE", as_of_date=D0)
    make_recommendation(db_session, asset_b, new_status="BEARISH", action="CONSIDER_DECREASE", as_of_date=D0)

    service = RecommendationOutcomeService(db_session, horizon=5)
    service.score_due_outcomes()

    increase_summary = service.get_review_summary(action="CONSIDER_INCREASE")
    decrease_summary = service.get_review_summary(action="CONSIDER_DECREASE")

    assert increase_summary.n == 1
    assert decrease_summary.n == 1
