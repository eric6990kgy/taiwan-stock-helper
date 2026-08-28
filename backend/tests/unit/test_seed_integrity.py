"""Verifies the demo dataset (PRD Sec.37) loads as intended: expected row
counts, every asset/price/fundamentals row correctly flagged as demo data,
no orphaned foreign keys, and both valuation_method conventions (A4) present
and used correctly.
"""

from app.database.seed import seed
from app.models import Account, Asset, Fundamentals, InvestmentThesis, PriceHistory, Transaction, User, Watchlist

EXPECTED_TICKERS = {"3653", "3533", "3491", "3515", "3563", "3551", "3483", "GLOBAL-ETF-01", "TWD-CASH"}


def test_seed_row_counts(db_session):
    seed(db_session)

    assert db_session.query(User).count() == 1
    assert db_session.query(Account).count() == 3
    assert db_session.query(Asset).count() == 9
    assert db_session.query(Transaction).count() == 7
    assert db_session.query(Watchlist).count() == 1
    assert db_session.query(InvestmentThesis).count() == 1
    assert db_session.query(Fundamentals).count() == 7  # one TTM row per TW stock only


def test_seed_asset_tickers_match_prd(db_session):
    seed(db_session)
    tickers = {a.ticker for a in db_session.query(Asset).all()}
    assert tickers == EXPECTED_TICKERS


def test_seed_all_assets_flagged_as_demo_data(db_session):
    seed(db_session)
    assets = db_session.query(Asset).all()
    assert all(a.is_demo_data is True for a in assets)


def test_seed_valuation_methods_correct(db_session):
    seed(db_session)
    global_etf = db_session.query(Asset).filter_by(ticker="GLOBAL-ETF-01").one()
    assert global_etf.valuation_method == "MANUAL_MARKET_VALUE"

    others = db_session.query(Asset).filter(Asset.ticker != "GLOBAL-ETF-01").all()
    assert all(a.valuation_method == "TRANSACTION_BASED" for a in others)


def test_seed_price_history_sources(db_session):
    seed(db_session)
    global_etf = db_session.query(Asset).filter_by(ticker="GLOBAL-ETF-01").one()
    manual_rows = db_session.query(PriceHistory).filter_by(asset_id=global_etf.id).all()
    assert len(manual_rows) == 3
    assert all(r.source == "MANUAL" for r in manual_rows)

    stock = db_session.query(Asset).filter_by(ticker="3653").one()
    mock_rows = db_session.query(PriceHistory).filter_by(asset_id=stock.id).all()
    assert len(mock_rows) == 11  # 10 days back + today
    assert all(r.source == "MOCK" for r in mock_rows)


def test_seed_transactions_reference_valid_accounts_and_assets(db_session):
    seed(db_session)
    account_ids = {a.id for a in db_session.query(Account).all()}
    asset_ids = {a.id for a in db_session.query(Asset).all()}

    for txn in db_session.query(Transaction).all():
        assert txn.account_id in account_ids
        assert txn.asset_id in asset_ids


def test_seed_global_etf_deposit_uses_amount_as_quantity_convention(db_session):
    """Per A4: MANUAL_MARKET_VALUE assets record deposits as quantity=amount,
    price=1, so invested-capital math (Phase 2) stays correct."""
    seed(db_session)
    global_etf = db_session.query(Asset).filter_by(ticker="GLOBAL-ETF-01").one()
    deposit = db_session.query(Transaction).filter_by(asset_id=global_etf.id, type="CASH_DEPOSIT").one()
    assert deposit.quantity == 120000
    assert deposit.price == 1


def test_seed_watchlist_and_thesis_reference_real_assets(db_session):
    seed(db_session)
    watchlist_entry = db_session.query(Watchlist).one()
    assert watchlist_entry.asset.ticker == "3491"

    thesis = db_session.query(InvestmentThesis).one()
    assert thesis.asset.ticker == "3653"
    assert thesis.status == "INTACT"
    assert len(thesis.key_metrics) == 3


def test_seed_is_idempotent(db_session):
    """Re-running seed() wipes and recreates rather than accumulating duplicates."""
    seed(db_session)
    seed(db_session)
    assert db_session.query(Asset).count() == 9
    assert db_session.query(Transaction).count() == 7
