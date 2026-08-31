"""Migration/schema correctness for Phase 5B: the new price_history/assets
columns and the new dividends table, built straight from the models (same
approach as the rest of tests/unit -- if the SQLAlchemy models and the
Alembic migration ever drift apart, `alembic upgrade head` against a fresh
DB is what actually proves the migration itself works, which Bash already
verified manually; this file proves the resulting *shape* is correct)."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app.models import Asset, Dividend, PriceHistory


def test_price_history_has_phase5b_columns(db_session):
    columns = {c["name"] for c in inspect(db_session.bind).get_columns("price_history")}
    assert {"adjusted_close", "trading_value", "pe_ratio", "pb_ratio", "dividend_yield"} <= columns


def test_assets_has_phase5b_columns(db_session):
    columns = {c["name"] for c in inspect(db_session.bind).get_columns("assets")}
    assert {"shares_outstanding", "listing_status"} <= columns


def test_assets_listing_status_defaults_to_active(db_session):
    asset = Asset(ticker="TEST1", name="Test", asset_type="STOCK", currency="TWD")
    db_session.add(asset)
    db_session.flush()
    assert asset.listing_status == "ACTIVE"


def test_assets_rejects_invalid_listing_status(db_session):
    db_session.add(Asset(ticker="TEST2", name="Test", asset_type="STOCK", currency="TWD", listing_status="ZOMBIE"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_price_history_valuation_columns_accept_values(db_session):
    asset = Asset(ticker="TEST3", name="Test", asset_type="STOCK", currency="TWD")
    db_session.add(asset)
    db_session.flush()

    row = PriceHistory(
        asset_id=asset.id,
        date=date(2026, 1, 1),
        close=Decimal("100"),
        adjusted_close=Decimal("99.5"),
        trading_value=Decimal("1000000"),
        pe_ratio=Decimal("15.2"),
        pb_ratio=Decimal("2.1"),
        dividend_yield=Decimal("0.03"),
        source="FINMIND",
    )
    db_session.add(row)
    db_session.flush()
    assert row.pe_ratio == Decimal("15.2")


def test_dividends_table_exists_with_expected_columns(db_session):
    columns = {c["name"] for c in inspect(db_session.bind).get_columns("dividends")}
    assert {"asset_id", "ex_dividend_date", "payment_date", "cash_dividend", "stock_dividend", "source"} <= columns


def test_dividends_unique_per_asset_and_ex_date(db_session):
    asset = Asset(ticker="TEST4", name="Test", asset_type="STOCK", currency="TWD")
    db_session.add(asset)
    db_session.flush()

    db_session.add(Dividend(asset_id=asset.id, ex_dividend_date=date(2026, 6, 13), cash_dividend=Decimal("3.5")))
    db_session.flush()
    db_session.add(Dividend(asset_id=asset.id, ex_dividend_date=date(2026, 6, 13), cash_dividend=Decimal("3.5")))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_dividends_requires_at_least_one_amount(db_session):
    asset = Asset(ticker="TEST5", name="Test", asset_type="STOCK", currency="TWD")
    db_session.add(asset)
    db_session.flush()

    db_session.add(Dividend(asset_id=asset.id, ex_dividend_date=date(2026, 6, 13)))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_dividends_allows_two_distributions_per_year_for_same_asset(db_session):
    """TSMC-style quarterly distributions -- more than one dividend event
    per asset per year must be allowed (the natural key is ex_dividend_date,
    not asset alone)."""
    asset = Asset(ticker="TEST6", name="Test", asset_type="STOCK", currency="TWD")
    db_session.add(asset)
    db_session.flush()

    db_session.add(Dividend(asset_id=asset.id, ex_dividend_date=date(2026, 3, 18), cash_dividend=Decimal("3.5")))
    db_session.add(Dividend(asset_id=asset.id, ex_dividend_date=date(2026, 6, 13), cash_dividend=Decimal("3.5")))
    db_session.flush()
    assert db_session.query(Dividend).filter_by(asset_id=asset.id).count() == 2
