"""RecommendationService tests -- change-only scanning, action
classification, and the risk gate (Phase 8). Seeds real DB rows via
repositories, same approach as test_scoring_service.py/test_signal_service.py,
since the service reads exclusively through the DB, never a mocked provider.
"""

from datetime import date, timedelta
from decimal import Decimal

from app.models.account import Account
from app.models.asset import Asset
from app.models.transaction import Transaction
from app.models.user import User
from app.models.watchlist import Watchlist
from app.repositories.price_repository import PriceRepository
from app.services.recommendation_service import RecommendationService

D0 = date(2026, 1, 1)
N_DAYS = 65


def make_asset(db, ticker="2330", sector=None) -> Asset:
    asset = Asset(ticker=ticker, name="Test Co", asset_type="STOCK", currency="TWD", is_demo_data=False, sector=sector)
    db.add(asset)
    db.flush()
    return asset


def add_to_watchlist(db, asset, status="WATCHING") -> Watchlist:
    entry = Watchlist(asset_id=asset.id, status=status)
    db.add(entry)
    db.flush()
    return entry


def seed_flat_prices(db, asset) -> None:
    prices = PriceRepository(db)
    for i in range(N_DAYS):
        prices.upsert(asset.id, D0 + timedelta(days=i), close=Decimal("100"), source="TEST")


def seed_rising_prices(db, asset) -> None:
    prices = PriceRepository(db)
    for i in range(N_DAYS):
        prices.upsert(asset.id, D0 + timedelta(days=i), close=Decimal(str(100 + i)), source="TEST")


def seed_falling_prices(db, asset) -> None:
    prices = PriceRepository(db)
    for i in range(N_DAYS):
        prices.upsert(asset.id, D0 + timedelta(days=i), close=Decimal(str(300 - i)), source="TEST")


def buy(db, asset, quantity="1000", price="100", on_date=D0) -> Transaction:
    user = User(name="Test User")
    db.add(user)
    db.flush()
    account = Account(user_id=user.id, name="Test Brokerage", account_type="BROKERAGE", currency="TWD")
    db.add(account)
    db.flush()
    txn = Transaction(
        account_id=account.id,
        asset_id=asset.id,
        date=on_date,
        type="BUY",
        quantity=Decimal(quantity),
        price=Decimal(price),
        fee=Decimal("0"),
        tax=Decimal("0"),
        currency="TWD",
    )
    db.add(txn)
    db.flush()
    return txn


# ---- change-only scanning ---------------------------------------------------


def test_first_scan_establishes_a_baseline_with_no_recommendations(db_session):
    asset = make_asset(db_session)
    add_to_watchlist(db_session, asset)
    seed_flat_prices(db_session, asset)

    outcomes = RecommendationService(db_session).run_daily_scan()
    assert outcomes == []


def test_unchanged_status_across_scans_produces_no_recommendation(db_session):
    asset = make_asset(db_session)
    add_to_watchlist(db_session, asset)
    seed_flat_prices(db_session, asset)

    service = RecommendationService(db_session)
    service.run_daily_scan()
    outcomes = service.run_daily_scan()
    assert outcomes == []


def test_rejected_watchlist_entries_are_excluded_from_the_scan(db_session):
    asset = make_asset(db_session)
    add_to_watchlist(db_session, asset, status="REJECTED")
    seed_rising_prices(db_session, asset)

    outcomes = RecommendationService(db_session).run_daily_scan()
    assert outcomes == []


# ---- action classification --------------------------------------------------


def test_bullish_transition_creates_a_consider_increase_recommendation(db_session):
    asset = make_asset(db_session)
    add_to_watchlist(db_session, asset)
    seed_flat_prices(db_session, asset)

    service = RecommendationService(db_session)
    service.run_daily_scan()  # NEUTRAL baseline

    seed_rising_prices(db_session, asset)
    outcomes = service.run_daily_scan()

    assert len(outcomes) == 1
    rec = outcomes[0].recommendation
    assert rec.action == "CONSIDER_INCREASE"
    assert rec.previous_status == "NEUTRAL"
    assert rec.new_status == "BULLISH"
    assert rec.risk_blocked is False
    assert len(rec.triggered_signals) > 0


def test_bearish_transition_creates_a_consider_decrease_recommendation(db_session):
    asset = make_asset(db_session)
    add_to_watchlist(db_session, asset)
    seed_flat_prices(db_session, asset)

    service = RecommendationService(db_session)
    service.run_daily_scan()  # NEUTRAL baseline

    seed_falling_prices(db_session, asset)
    outcomes = service.run_daily_scan()

    assert len(outcomes) == 1
    rec = outcomes[0].recommendation
    assert rec.action == "CONSIDER_DECREASE"
    assert rec.new_status == "BEARISH"
    assert rec.risk_blocked is False  # never gated -- reducing/watching is always allowed


def test_neutral_transition_from_bullish_creates_a_watch_recommendation(db_session):
    asset = make_asset(db_session)
    add_to_watchlist(db_session, asset)
    seed_rising_prices(db_session, asset)

    service = RecommendationService(db_session)
    service.run_daily_scan()  # BULLISH baseline

    seed_flat_prices(db_session, asset)
    outcomes = service.run_daily_scan()

    assert len(outcomes) == 1
    rec = outcomes[0].recommendation
    assert rec.action == "WATCH"
    assert rec.previous_status == "BULLISH"
    assert rec.new_status == "NEUTRAL"
    assert rec.risk_blocked is False


# ---- risk gate ----------------------------------------------------------------


def test_consider_increase_blocked_when_position_already_at_limit(db_session):
    asset = make_asset(db_session, ticker="2330")
    add_to_watchlist(db_session, asset)
    seed_flat_prices(db_session, asset)
    buy(db_session, asset)  # the only STOCK holding -- 100% of the sleeve, over the 15% limit

    service = RecommendationService(db_session)
    service.run_daily_scan()  # NEUTRAL baseline

    seed_rising_prices(db_session, asset)
    outcomes = service.run_daily_scan()

    assert len(outcomes) == 1
    rec = outcomes[0].recommendation
    assert rec.action == "CONSIDER_INCREASE"
    assert rec.risk_blocked is True
    assert "上限" in rec.risk_block_reason


def test_risk_gate_blocks_on_drawdown_hard_stop(db_session):
    """Tests the gate directly (rather than through a full scan) so the
    drawdown scenario doesn't have to simultaneously satisfy a realistic
    technical-signal uptrend -- get_drawdown() reads date.today(), so this
    seeds a real peak-then-crash shape anchored to today."""
    asset = make_asset(db_session, ticker="2330")
    today = date.today()
    peak_date = today - timedelta(days=300)

    prices = PriceRepository(db_session)
    prices.upsert(asset.id, peak_date, close=Decimal("1000"), source="TEST")
    prices.upsert(asset.id, today, close=Decimal("700"), source="TEST")  # -30% off peak
    buy(db_session, asset, quantity="10", price="1000", on_date=peak_date)

    service = RecommendationService(db_session)
    blocked, reason = service._check_risk_gate("2330")

    assert blocked is True
    assert "回撤" in reason
    assert "HARD_STOP" in reason
