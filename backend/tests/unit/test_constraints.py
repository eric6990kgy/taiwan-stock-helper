"""Verifies the DB-level guardrails from the schema decisions (PRD Sec.18,
Sec.39, and A6/A7/A9/A10 from the architecture review): required CHECK
constraints, UNIQUE constraints, and FK enforcement all actually fire.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Account, Asset, Fundamentals, InvestmentThesis, PriceHistory, Transaction, User, Watchlist


def _make_user_account_asset(db):
    user = User(name="Test User")
    db.add(user)
    db.flush()
    account = Account(user_id=user.id, name="Test Brokerage", account_type="BROKERAGE", currency="TWD")
    asset = Asset(ticker="TEST1", name="Test Co", asset_type="STOCK", currency="TWD")
    db.add_all([account, asset])
    db.flush()
    return user, account, asset


# ---- Transaction CHECK constraints (A9, PRD Sec.39) ----------------------


@pytest.mark.parametrize(
    "quantity,price,fee,tax",
    [
        (Decimal("0"), Decimal("100"), Decimal("0"), Decimal("0")),      # quantity must be > 0
        (Decimal("-5"), Decimal("100"), Decimal("0"), Decimal("0")),     # negative quantity
        (Decimal("10"), Decimal("0"), Decimal("0"), Decimal("0")),       # price must be > 0
        (Decimal("10"), Decimal("100"), Decimal("-1"), Decimal("0")),    # fee must be >= 0
        (Decimal("10"), Decimal("100"), Decimal("0"), Decimal("-1")),    # tax must be >= 0
    ],
)
def test_transaction_rejects_invalid_amounts(db_session, quantity, price, fee, tax):
    _, account, asset = _make_user_account_asset(db_session)
    db_session.add(
        Transaction(
            account_id=account.id,
            asset_id=asset.id,
            date=date(2026, 1, 1),
            type="BUY",
            quantity=quantity,
            price=price,
            fee=fee,
            tax=tax,
            currency="TWD",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_transaction_rejects_invalid_type(db_session):
    _, account, asset = _make_user_account_asset(db_session)
    db_session.add(
        Transaction(
            account_id=account.id,
            asset_id=asset.id,
            date=date(2026, 1, 1),
            type="SHORT",  # not in TRANSACTION_TYPES
            quantity=Decimal("1"),
            price=Decimal("1"),
            currency="TWD",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_transaction_valid_row_persists(db_session):
    _, account, asset = _make_user_account_asset(db_session)
    db_session.add(
        Transaction(
            account_id=account.id,
            asset_id=asset.id,
            date=date(2026, 1, 1),
            type="BUY",
            quantity=Decimal("10"),
            price=Decimal("100"),
            fee=Decimal("20"),
            tax=Decimal("0"),
            currency="TWD",
        )
    )
    db_session.flush()
    assert db_session.query(Transaction).count() == 1


# ---- FK enforcement --------------------------------------------------------


def test_transaction_rejects_unknown_account(db_session):
    _, _, asset = _make_user_account_asset(db_session)
    db_session.add(
        Transaction(
            account_id=9999,
            asset_id=asset.id,
            date=date(2026, 1, 1),
            type="BUY",
            quantity=Decimal("1"),
            price=Decimal("1"),
            currency="TWD",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_transaction_rejects_unknown_asset(db_session):
    _, account, _ = _make_user_account_asset(db_session)
    db_session.add(
        Transaction(
            account_id=account.id,
            asset_id=9999,
            date=date(2026, 1, 1),
            type="BUY",
            quantity=Decimal("1"),
            price=Decimal("1"),
            currency="TWD",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


# ---- Asset-level CHECK constraints ----------------------------------------


def test_asset_rejects_invalid_asset_type(db_session):
    db_session.add(Asset(ticker="BAD1", name="Bad Co", asset_type="CRYPTO", currency="TWD"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_asset_rejects_invalid_valuation_method(db_session):
    db_session.add(
        Asset(
            ticker="BAD2",
            name="Bad Co",
            asset_type="STOCK",
            currency="TWD",
            valuation_method="LIVE_QUOTE",  # not a recognized method
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_asset_ticker_must_be_unique(db_session):
    db_session.add(Asset(ticker="DUPE", name="First", asset_type="STOCK", currency="TWD"))
    db_session.flush()
    db_session.add(Asset(ticker="DUPE", name="Second", asset_type="STOCK", currency="TWD"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_account_rejects_invalid_account_type(db_session):
    user = User(name="Test User")
    db_session.add(user)
    db_session.flush()
    db_session.add(Account(user_id=user.id, name="Weird", account_type="CRYPTO_WALLET", currency="TWD"))
    with pytest.raises(IntegrityError):
        db_session.flush()


# ---- Watchlist / Thesis: one row per asset (A6/A7) -------------------------


def test_watchlist_one_entry_per_asset(db_session):
    _, _, asset = _make_user_account_asset(db_session)
    db_session.add(Watchlist(asset_id=asset.id, status="WATCHING"))
    db_session.flush()
    db_session.add(Watchlist(asset_id=asset.id, status="RESEARCHING"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_watchlist_rejects_invalid_status(db_session):
    _, _, asset = _make_user_account_asset(db_session)
    db_session.add(Watchlist(asset_id=asset.id, status="MAYBE"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_thesis_one_entry_per_asset(db_session):
    _, _, asset = _make_user_account_asset(db_session)
    db_session.add(InvestmentThesis(asset_id=asset.id, thesis="a", status="INTACT"))
    db_session.flush()
    db_session.add(InvestmentThesis(asset_id=asset.id, thesis="b", status="INTACT"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_thesis_rejects_invalid_status(db_session):
    _, _, asset = _make_user_account_asset(db_session)
    db_session.add(InvestmentThesis(asset_id=asset.id, thesis="a", status="ON_FIRE"))
    with pytest.raises(IntegrityError):
        db_session.flush()


# ---- price_history / fundamentals uniqueness -------------------------------


def test_price_history_unique_per_asset_date(db_session):
    _, _, asset = _make_user_account_asset(db_session)
    db_session.add(PriceHistory(asset_id=asset.id, date=date(2026, 1, 1), close=Decimal("100")))
    db_session.flush()
    db_session.add(PriceHistory(asset_id=asset.id, date=date(2026, 1, 1), close=Decimal("101")))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_price_history_rejects_nonpositive_close(db_session):
    _, _, asset = _make_user_account_asset(db_session)
    db_session.add(PriceHistory(asset_id=asset.id, date=date(2026, 1, 1), close=Decimal("0")))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_fundamentals_unique_per_asset_period(db_session):
    _, _, asset = _make_user_account_asset(db_session)
    db_session.add(Fundamentals(asset_id=asset.id, period="TTM", source="MOCK"))
    db_session.flush()
    db_session.add(Fundamentals(asset_id=asset.id, period="TTM", source="MOCK"))
    with pytest.raises(IntegrityError):
        db_session.flush()
