"""Direct repository + MockMarketDataProvider tests for the three Phase 6
datasets (institutional flow, margin trading, monthly revenue) -- insert,
upsert-on-duplicate-key, and per-asset isolation, independent of the
ingestion-service-level tests in test_market_data_ingestion.py.
"""

from datetime import date
from decimal import Decimal

from app.models.asset import Asset
from app.providers.mock_provider import MockMarketDataProvider
from app.repositories.institutional_flow_repository import InstitutionalFlowRepository
from app.repositories.margin_trading_repository import MarginTradingRepository
from app.repositories.monthly_revenue_repository import MonthlyRevenueRepository


def make_asset(db, ticker="3653") -> Asset:
    asset = Asset(ticker=ticker, name="Test Co", asset_type="STOCK", currency="TWD")
    db.add(asset)
    db.flush()
    return asset


# ---- InstitutionalFlowRepository --------------------------------------------------


def test_institutional_flow_insert_and_range(db_session):
    asset = make_asset(db_session)
    repo = InstitutionalFlowRepository(db_session)
    repo.upsert(asset.id, date(2026, 8, 27), foreign_net=100, source="FINMIND")
    repo.upsert(asset.id, date(2026, 8, 28), foreign_net=200, source="FINMIND")

    rows = repo.range(asset.id)
    assert [r.date for r in rows] == [date(2026, 8, 27), date(2026, 8, 28)]

    filtered = repo.range(asset.id, start=date(2026, 8, 28))
    assert [r.date for r in filtered] == [date(2026, 8, 28)]


def test_institutional_flow_upsert_same_date_updates_in_place(db_session):
    asset = make_asset(db_session)
    repo = InstitutionalFlowRepository(db_session)
    repo.upsert(asset.id, date(2026, 8, 27), foreign_net=100, source="FINMIND")
    repo.upsert(asset.id, date(2026, 8, 27), foreign_net=999, source="FINMIND")

    rows = repo.range(asset.id)
    assert len(rows) == 1
    assert rows[0].foreign_net == 999


def test_institutional_flow_isolated_per_asset(db_session):
    a1 = make_asset(db_session, ticker="3653")
    a2 = make_asset(db_session, ticker="3533")
    repo = InstitutionalFlowRepository(db_session)
    repo.upsert(a1.id, date(2026, 8, 27), foreign_net=100, source="FINMIND")
    repo.upsert(a2.id, date(2026, 8, 27), foreign_net=200, source="FINMIND")

    assert len(repo.range(a1.id)) == 1
    assert repo.range(a1.id)[0].foreign_net == 100
    assert repo.range(a2.id)[0].foreign_net == 200


# ---- MarginTradingRepository -------------------------------------------------------


def test_margin_trading_insert_and_upsert(db_session):
    asset = make_asset(db_session)
    repo = MarginTradingRepository(db_session)
    repo.upsert(asset.id, date(2026, 8, 20), margin_balance=28308, source="FINMIND")
    repo.upsert(asset.id, date(2026, 8, 20), margin_balance=28999, source="FINMIND")

    rows = repo.range(asset.id)
    assert len(rows) == 1
    assert rows[0].margin_balance == 28999


def test_margin_trading_multiple_tickers_isolated(db_session):
    a1 = make_asset(db_session, ticker="3653")
    a2 = make_asset(db_session, ticker="3533")
    repo = MarginTradingRepository(db_session)
    repo.upsert(a1.id, date(2026, 8, 20), margin_balance=100, source="FINMIND")
    repo.upsert(a2.id, date(2026, 8, 20), margin_balance=200, source="FINMIND")

    assert repo.range(a1.id)[0].margin_balance == 100
    assert repo.range(a2.id)[0].margin_balance == 200


# ---- MonthlyRevenueRepository -------------------------------------------------------


def test_monthly_revenue_insert_and_list(db_session):
    asset = make_asset(db_session)
    repo = MonthlyRevenueRepository(db_session)
    repo.upsert(asset.id, 2026, 6, revenue=Decimal("100"), source="FINMIND")
    repo.upsert(asset.id, 2026, 7, revenue=Decimal("110"), source="FINMIND")

    rows = repo.list_by_asset(asset.id)
    assert [(r.revenue_year, r.revenue_month) for r in rows] == [(2026, 6), (2026, 7)]


def test_monthly_revenue_upsert_same_period_updates_in_place(db_session):
    asset = make_asset(db_session)
    repo = MonthlyRevenueRepository(db_session)
    repo.upsert(asset.id, 2026, 7, revenue=Decimal("100"), source="FINMIND")
    repo.upsert(asset.id, 2026, 7, revenue=Decimal("150"), source="FINMIND")

    rows = repo.list_by_asset(asset.id)
    assert len(rows) == 1
    assert rows[0].revenue == Decimal("150")


def test_monthly_revenue_different_years_same_month_are_distinct_rows(db_session):
    asset = make_asset(db_session)
    repo = MonthlyRevenueRepository(db_session)
    repo.upsert(asset.id, 2025, 7, revenue=Decimal("90"), source="FINMIND")
    repo.upsert(asset.id, 2026, 7, revenue=Decimal("100"), source="FINMIND")

    rows = repo.list_by_asset(asset.id)
    assert len(rows) == 2


# ---- MockMarketDataProvider wiring --------------------------------------------------


def test_mock_provider_serves_institutional_flows_from_repository(db_session):
    asset = make_asset(db_session)
    InstitutionalFlowRepository(db_session).upsert(asset.id, date(2026, 8, 27), foreign_net=500, source="FINMIND")

    provider = MockMarketDataProvider(db_session)
    flows = provider.get_institutional_flows("3653")
    assert len(flows) == 1
    assert flows[0].foreign_net == 500
    assert flows[0].source == "FINMIND"


def test_mock_provider_serves_margin_trading_from_repository(db_session):
    asset = make_asset(db_session)
    MarginTradingRepository(db_session).upsert(asset.id, date(2026, 8, 20), margin_balance=28308, source="FINMIND")

    provider = MockMarketDataProvider(db_session)
    rows = provider.get_margin_trading("3653")
    assert len(rows) == 1
    assert rows[0].margin_balance == 28308


def test_mock_provider_serves_monthly_revenue_from_repository(db_session):
    asset = make_asset(db_session)
    MonthlyRevenueRepository(db_session).upsert(asset.id, 2026, 7, revenue=Decimal("467580548000"), source="FINMIND")

    provider = MockMarketDataProvider(db_session)
    rows = provider.get_monthly_revenue("3653")
    assert len(rows) == 1
    assert rows[0].revenue_year == 2026
    assert rows[0].revenue_month == 7
    assert rows[0].revenue == Decimal("467580548000")
