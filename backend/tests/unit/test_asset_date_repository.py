"""Tests for the shared AssetDateRepository base (app/repositories/
asset_date_repository.py) -- the range/get_by_asset_and_date/upsert pattern
that Dividend/InstitutionalFlow/MarginTrading/Price repositories all extend.
Exercised directly against InstitutionalFlowRepository (a plain subclass with
no extra behavior) rather than duplicated per concrete repository -- each
concrete repository's own test file (test_phase6_repositories.py,
test_market_data_ingestion.py) covers that it's wired up correctly.
"""

from datetime import date

import pytest

from app.models.asset import Asset
from app.repositories.institutional_flow_repository import InstitutionalFlowRepository


def make_asset(db, ticker="3653") -> Asset:
    asset = Asset(ticker=ticker, name="Test Co", asset_type="STOCK", currency="TWD")
    db.add(asset)
    db.flush()
    return asset


def test_upsert_update_path_rejects_a_misspelled_field(db_session):
    """Regression test: the create path already raises TypeError on a bad
    kwarg; the update path used to silently setattr a non-persisted plain
    attribute instead of raising -- now both paths fail the same way."""
    asset = make_asset(db_session)
    repo = InstitutionalFlowRepository(db_session)
    repo.upsert(asset.id, date(2026, 8, 27), foreign_net=100, source="FINMIND")  # create path, row now exists

    with pytest.raises(AttributeError):
        repo.upsert(asset.id, date(2026, 8, 27), dealer_net_=5)  # update path, misspelled field


def test_upsert_create_path_still_raises_on_a_misspelled_field(db_session):
    asset = make_asset(db_session)
    repo = InstitutionalFlowRepository(db_session)
    with pytest.raises(TypeError):
        repo.upsert(asset.id, date(2026, 8, 27), dealer_net_=5)  # no existing row -> create path
