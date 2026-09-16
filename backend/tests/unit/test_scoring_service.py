"""ScoringService tests -- seeds real DB rows via repositories (same
approach as test_phase6_repositories.py) since ScoringService reads
exclusively through MockMarketDataProvider, never a mocked provider."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models.asset import Asset
from app.models.score import Score
from app.providers.market_data_provider import AssetNotFoundError
from app.repositories.fundamentals_repository import FundamentalsRepository
from app.repositories.price_repository import PriceRepository
from app.services.scoring_service import ScoringService


def make_asset(db, ticker="3653", asset_type="STOCK") -> Asset:
    asset = Asset(ticker=ticker, name="Test Co", asset_type=asset_type, currency="TWD", is_demo_data=False)
    db.add(asset)
    db.flush()
    return asset


def make_taiex(db) -> Asset:
    return make_asset(db, ticker="TAIEX", asset_type="INDEX")


def test_compute_and_store_all_none_when_no_data_at_all(db_session):
    asset = make_asset(db_session)
    on_date = date(2026, 8, 28)
    PriceRepository(db_session).upsert(asset.id, on_date, close=Decimal("100"), source="FINMIND")

    service = ScoringService(db_session)
    row = service.compute_and_store(asset.ticker, on_date)

    assert row.value_score is None
    assert row.growth_score is None
    assert row.momentum_score is None
    assert row.quality_score is None
    assert row.composite_score is None
    assert row.regime is None
    assert sorted(row.missing_components.split(",")) == ["growth", "momentum", "quality", "value"]


def test_compute_and_store_computes_value_score_from_valuation(db_session):
    asset = make_asset(db_session)
    on_date = date(2026, 8, 28)
    PriceRepository(db_session).upsert(
        asset.id, on_date, close=Decimal("100"), pe_ratio=Decimal("10"), pb_ratio=Decimal("1"), source="FINMIND"
    )

    service = ScoringService(db_session)
    row = service.compute_and_store(asset.ticker, on_date)

    assert row.value_score == Decimal("100.00")
    assert "value" not in row.missing_components.split(",")


def test_compute_and_store_upserts_the_same_date_instead_of_duplicating(db_session):
    asset = make_asset(db_session)
    on_date = date(2026, 8, 28)
    prices = PriceRepository(db_session)
    prices.upsert(asset.id, on_date, close=Decimal("100"), pe_ratio=Decimal("10"), source="FINMIND")

    service = ScoringService(db_session)
    service.compute_and_store(asset.ticker, on_date)

    prices.upsert(asset.id, on_date, pe_ratio=Decimal("30"))  # a worse PE, re-ingested for the same date
    service.compute_and_store(asset.ticker, on_date)

    rows = db_session.query(Score).filter_by(asset_id=asset.id).all()
    assert len(rows) == 1
    assert rows[0].value_score == Decimal("50.00")  # reflects the updated PE, not the first computation


def test_compute_and_store_uses_taiex_history_for_regime(db_session):
    asset = make_asset(db_session)
    taiex = make_taiex(db_session)
    on_date = date(2026, 8, 28)

    prices = PriceRepository(db_session)
    prices.upsert(asset.id, on_date, close=Decimal("100"), source="FINMIND")

    start = on_date - timedelta(days=199)
    for i in range(200):
        prices.upsert(taiex.id, start + timedelta(days=i), close=Decimal(str(15000 + i * 5)), source="FINMIND")

    service = ScoringService(db_session)
    row = service.compute_and_store(asset.ticker, on_date)

    assert row.regime == "BULL"


def test_compute_and_store_regime_none_when_taiex_not_provisioned(db_session):
    """No TAIEX asset exists at all -- regime falls back to None rather
    than crashing the rest of the score computation."""
    asset = make_asset(db_session)
    on_date = date(2026, 8, 28)
    PriceRepository(db_session).upsert(asset.id, on_date, close=Decimal("100"), pe_ratio=Decimal("10"), source="FINMIND")

    service = ScoringService(db_session)
    row = service.compute_and_store(asset.ticker, on_date)

    assert row.regime is None
    assert row.value_score == Decimal("100.00")  # unaffected by the missing TAIEX data


def test_compute_and_store_quality_score_from_fundamentals_and_valuation(db_session):
    asset = make_asset(db_session)
    on_date = date(2026, 8, 28)
    PriceRepository(db_session).upsert(asset.id, on_date, close=Decimal("100"), dividend_yield=Decimal("5"), source="FINMIND")
    FundamentalsRepository(db_session).upsert(
        asset.id, "TTM", roe=Decimal("0.25"), debt_ratio=Decimal("0.3"), source="FINMIND"
    )

    service = ScoringService(db_session)
    row = service.compute_and_store(asset.ticker, on_date)

    assert row.quality_score == Decimal("100.00")
    assert "quality" not in row.missing_components.split(",")


def test_compute_and_store_unknown_ticker_raises_asset_not_found(db_session):
    service = ScoringService(db_session)
    with pytest.raises(AssetNotFoundError):
        service.compute_and_store("NOPE", date(2026, 8, 28))
