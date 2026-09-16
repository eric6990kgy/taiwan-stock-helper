"""SignalService tests -- seeds real DB rows via repositories (same
approach as test_scoring_service.py), since SignalService reads
exclusively through MockMarketDataProvider plus ScoreRepository, never a
mocked provider."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models.asset import Asset
from app.repositories.institutional_flow_repository import InstitutionalFlowRepository
from app.repositories.price_repository import PriceRepository
from app.repositories.score_repository import ScoreRepository
from app.services.exceptions import NotFoundError
from app.services.signal_service import SignalService


def make_asset(db, ticker="3653") -> Asset:
    asset = Asset(ticker=ticker, name="Test Co", asset_type="STOCK", currency="TWD", is_demo_data=False)
    db.add(asset)
    db.flush()
    return asset


def test_unknown_ticker_raises_not_found(db_session):
    service = SignalService(db_session)
    with pytest.raises(NotFoundError):
        service.get_signals("NOPE")


def test_get_signals_returns_a_signal_for_every_category(db_session):
    asset = make_asset(db_session)
    on_date = date(2026, 8, 28)
    PriceRepository(db_session).upsert(asset.id, on_date, close=Decimal("100"), source="FINMIND")

    result = SignalService(db_session).get_signals(asset.ticker)

    ids = {s.id for s in result.signals}
    assert ids == {
        "PRICE_ABOVE_SMA20",
        "PRICE_ABOVE_SMA60",
        "RSI_BULLISH",
        "MACD_BULLISH",
        "FOREIGN_NET_BUYING",
        "INVESTMENT_TRUST_NET_BUYING",
        "REVENUE_GROWTH_POSITIVE",
        "REVENUE_GROWTH_ACCELERATING",
        "COMPOSITE_SCORE",
    }
    assert result.as_of == on_date


def test_as_of_produces_reproducible_historical_results(db_session):
    """Passing an earlier as_of must reflect only data known as of that
    date -- a later price written after it must not change the result."""
    asset = make_asset(db_session)
    prices = PriceRepository(db_session)
    early_date = date(2026, 8, 20)
    prices.upsert(asset.id, early_date, close=Decimal("100"), source="FINMIND")

    service = SignalService(db_session)
    before = service.get_signals(asset.ticker, as_of=early_date)

    later_date = date(2026, 8, 21)
    prices.upsert(asset.id, later_date, close=Decimal("99999"), source="FINMIND")
    after = service.get_signals(asset.ticker, as_of=early_date)

    assert before.signals == after.signals
    assert after.as_of == early_date


def test_default_as_of_is_the_latest_price_date(db_session):
    asset = make_asset(db_session)
    prices = PriceRepository(db_session)
    prices.upsert(asset.id, date(2026, 8, 20), close=Decimal("100"), source="FINMIND")
    prices.upsert(asset.id, date(2026, 8, 21), close=Decimal("105"), source="FINMIND")

    result = SignalService(db_session).get_signals(asset.ticker)
    assert result.as_of == date(2026, 8, 21)


def test_composite_signal_reads_persisted_score_without_recomputing(db_session):
    """Writes a Score row directly (bypassing ScoringService entirely) with
    a composite_score that would be impossible to derive from the
    (nonexistent) valuation/fundamentals data in this test -- if
    SignalService recomputed instead of reading the persisted row, the
    composite signal would come back UNAVAILABLE instead of BULLISH."""
    asset = make_asset(db_session)
    on_date = date(2026, 8, 28)
    PriceRepository(db_session).upsert(asset.id, on_date, close=Decimal("100"), source="FINMIND")
    ScoreRepository(db_session).upsert(
        asset.id,
        on_date,
        value_score=None,
        growth_score=None,
        momentum_score=None,
        quality_score=None,
        composite_score=Decimal("75.00"),
        regime="BULL",
        missing_components="value,growth,momentum,quality",
        source="CALCULATED",
    )

    result = SignalService(db_session).get_signals(asset.ticker, as_of=on_date)

    composite_signal = next(s for s in result.signals if s.id == "COMPOSITE_SCORE")
    assert composite_signal.status == "BULLISH"
    assert result.composite_score == Decimal("75.00")
    assert result.regime == "BULL"


def test_composite_signal_unavailable_when_no_score_persisted(db_session):
    asset = make_asset(db_session)
    on_date = date(2026, 8, 28)
    PriceRepository(db_session).upsert(asset.id, on_date, close=Decimal("100"), source="FINMIND")

    result = SignalService(db_session).get_signals(asset.ticker)

    composite_signal = next(s for s in result.signals if s.id == "COMPOSITE_SCORE")
    assert composite_signal.status == "UNAVAILABLE"
    assert result.composite_score is None


def test_institutional_signals_use_flow_history(db_session):
    asset = make_asset(db_session)
    prices = PriceRepository(db_session)
    flows = InstitutionalFlowRepository(db_session)
    on_date = date(2026, 8, 28)
    prices.upsert(asset.id, on_date, close=Decimal("100"), source="FINMIND")
    for i in range(5):
        flows.upsert(asset.id, on_date - timedelta(days=4 - i), foreign_net=100, investment_trust_net=100, source="FINMIND")

    result = SignalService(db_session).get_signals(asset.ticker, as_of=on_date)

    foreign = next(s for s in result.signals if s.id == "FOREIGN_NET_BUYING")
    assert foreign.status == "BULLISH"
