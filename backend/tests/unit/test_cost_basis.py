"""Tests the transaction replay engine: weighted-average cost, realized P&L,
chronological/backdated replay, and the per-(account,asset) independence
guarantee (architecture decision A2). No DB, no ORM — TransactionInput is
built by hand in every test.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.analytics.cost_basis import calculate_positions, empty_position, replay_transactions
from app.analytics.exceptions import InsufficientSharesError, MixedPositionError
from app.analytics.types import TransactionInput


def txn(id, account_id=1, asset_id=1, date_=date(2026, 1, 1), type="BUY", quantity="0", price="0", fee="0", tax="0"):
    return TransactionInput(
        id=id,
        account_id=account_id,
        asset_id=asset_id,
        date=date_,
        type=type,
        quantity=Decimal(quantity),
        price=Decimal(price),
        fee=Decimal(fee),
        tax=Decimal(tax),
    )


# ---- Single BUY / multiple BUYs (weighted average cost) -------------------


def test_single_buy():
    pos = replay_transactions([txn(1, type="BUY", quantity="10", price="100")])
    assert pos.remaining_shares == Decimal("10")
    assert pos.average_cost == Decimal("100")
    assert pos.remaining_cost == Decimal("1000")
    assert pos.realized_pnl == Decimal("0")


def test_multiple_buys_weighted_average_cost():
    pos = replay_transactions(
        [
            txn(1, date_=date(2026, 3, 10), type="BUY", quantity="10", price="100"),
            txn(2, date_=date(2026, 5, 20), type="BUY", quantity="10", price="120"),
        ]
    )
    assert pos.remaining_shares == Decimal("20")
    assert pos.remaining_cost == Decimal("2200")
    assert pos.average_cost == Decimal("110")


# ---- Partial / full / multiple SELLs ---------------------------------------


def test_partial_sell_realizes_pnl_at_average_cost():
    pos = replay_transactions(
        [
            txn(1, date_=date(2026, 1, 1), type="BUY", quantity="10", price="100"),
            txn(2, date_=date(2026, 2, 1), type="BUY", quantity="10", price="120"),
            txn(3, date_=date(2026, 3, 1), type="SELL", quantity="5", price="130"),
        ]
    )
    # avg cost after both buys = 110; sell 5 @ 130 -> proceeds 650, cost sold 550
    assert pos.remaining_shares == Decimal("15")
    assert pos.average_cost == Decimal("110")  # unaffected by a sell
    assert pos.remaining_cost == Decimal("1650")
    assert pos.realized_pnl == Decimal("100")


def test_full_sell_closes_position_to_exact_zero():
    pos = replay_transactions(
        [
            txn(1, date_=date(2026, 1, 1), type="BUY", quantity="10", price="100"),
            txn(2, date_=date(2026, 2, 1), type="BUY", quantity="10", price="120"),
            txn(3, date_=date(2026, 3, 1), type="SELL", quantity="20", price="140"),
        ]
    )
    assert pos.remaining_shares == Decimal("0")
    assert pos.remaining_cost == Decimal("0")  # snapped exactly to zero, no rounding dust
    # proceeds 20*140=2800, cost sold 20*110=2200 -> realized 600
    assert pos.realized_pnl == Decimal("600")


def test_multiple_sells_each_use_average_cost_at_time_of_sale():
    pos = replay_transactions(
        [
            txn(1, date_=date(2026, 1, 1), type="BUY", quantity="10", price="100"),  # avg 100
            txn(2, date_=date(2026, 2, 1), type="SELL", quantity="4", price="150"),  # realize (150-100)*4=200
            txn(3, date_=date(2026, 3, 1), type="BUY", quantity="10", price="130"),  # remaining 6@100=600 + 10@130=1300 -> 1900/16=118.75
            txn(4, date_=date(2026, 4, 1), type="SELL", quantity="6", price="160"),  # realize (160-118.75)*6=247.5
        ]
    )
    assert pos.remaining_shares == Decimal("10")
    assert pos.average_cost == Decimal("118.75")
    assert pos.realized_pnl == Decimal("200") + Decimal("247.5")


# ---- Backdated transactions -------------------------------------------------


def test_backdated_transaction_recalculates_realized_pnl_correctly():
    """A BUY that actually happened between an existing BUY and SELL is
    entered later (higher id) but with an earlier date. Replay must use
    date order, not insertion order, or realized P&L on the SELL comes out
    wrong (using the pre-backdate average cost instead of the corrected one).
    """
    original_buy = txn(1, date_=date(2026, 1, 1), type="BUY", quantity="10", price="100")
    original_sell = txn(2, date_=date(2026, 3, 1), type="SELL", quantity="5", price="140")
    backdated_buy = txn(3, date_=date(2026, 2, 1), type="BUY", quantity="10", price="120")

    # Passed in insertion order (buy, sell, backdated-buy) -- NOT chronological.
    pos = replay_transactions([original_buy, original_sell, backdated_buy])

    # Correct (date-sorted) replay: buy10@100 -> buy10@120 (avg 110) -> sell5@140
    # cost_of_sold = 5*110 = 550, proceeds = 700, realized = 150
    assert pos.average_cost == Decimal("110")
    assert pos.remaining_shares == Decimal("15")
    assert pos.remaining_cost == Decimal("1650")
    assert pos.realized_pnl == Decimal("150")

    # Confirms this differs from the (wrong) insertion-order result of 200,
    # i.e. sorting genuinely changed the outcome rather than being a no-op.
    assert pos.realized_pnl != Decimal("200")


def test_transaction_order_in_input_list_does_not_matter():
    txns = [
        txn(1, date_=date(2026, 1, 1), type="BUY", quantity="10", price="100"),
        txn(2, date_=date(2026, 2, 1), type="BUY", quantity="5", price="90"),
        txn(3, date_=date(2026, 3, 1), type="SELL", quantity="8", price="130"),
    ]
    forward = replay_transactions(txns)
    backward = replay_transactions(list(reversed(txns)))
    shuffled = replay_transactions([txns[1], txns[2], txns[0]])

    assert forward == backward == shuffled


# ---- Insufficient shares ----------------------------------------------------


def test_sell_more_than_held_raises():
    with pytest.raises(InsufficientSharesError) as exc_info:
        replay_transactions(
            [
                txn(1, date_=date(2026, 1, 1), type="BUY", quantity="10", price="100"),
                txn(2, date_=date(2026, 2, 1), type="SELL", quantity="15", price="120"),
            ]
        )
    err = exc_info.value
    assert err.requested == Decimal("15")
    assert err.available == Decimal("10")
    assert err.account_id == 1
    assert err.asset_id == 1


def test_sell_more_than_held_raises_even_when_later_buy_would_have_covered_it():
    """A SELL is checked against shares available *at that point in time* —
    a later (chronologically) BUY cannot retroactively cover an earlier
    oversell."""
    with pytest.raises(InsufficientSharesError):
        replay_transactions(
            [
                txn(1, date_=date(2026, 1, 1), type="BUY", quantity="5", price="100"),
                txn(2, date_=date(2026, 2, 1), type="SELL", quantity="10", price="120"),
                txn(3, date_=date(2026, 3, 1), type="BUY", quantity="10", price="100"),
            ]
        )


# ---- Zero / empty positions --------------------------------------------------


def test_empty_position_helper_returns_all_zeros():
    pos = empty_position(account_id=1, asset_id=42)
    assert pos.remaining_shares == Decimal("0")
    assert pos.average_cost == Decimal("0")
    assert pos.remaining_cost == Decimal("0")
    assert pos.realized_pnl == Decimal("0")
    assert pos.transaction_count == 0


def test_replay_transactions_rejects_empty_list():
    with pytest.raises(ValueError):
        replay_transactions([])


# ---- Fees and taxes ----------------------------------------------------------


def test_buy_fee_is_capitalized_into_cost_basis():
    pos = replay_transactions([txn(1, type="BUY", quantity="10", price="100", fee="50")])
    assert pos.remaining_cost == Decimal("1050")  # 1000 + fee
    assert pos.average_cost == Decimal("105")
    assert pos.total_fees_paid == Decimal("50")


def test_sell_fee_and_tax_reduce_proceeds_and_realized_pnl():
    pos = replay_transactions(
        [
            txn(1, date_=date(2026, 1, 1), type="BUY", quantity="10", price="100", fee="50"),  # avg 105
            txn(2, date_=date(2026, 2, 1), type="SELL", quantity="10", price="120", fee="30", tax="10"),
        ]
    )
    # proceeds = 1200 - 30 - 10 = 1160; cost sold = 10*105 = 1050; realized = 110
    assert pos.realized_pnl == Decimal("110")
    assert pos.total_fees_paid == Decimal("80")
    assert pos.total_tax_paid == Decimal("10")
    assert pos.remaining_shares == Decimal("0")


# ---- Dividends ----------------------------------------------------------------


def test_dividend_adds_income_without_touching_shares_or_cost():
    pos = replay_transactions(
        [
            txn(1, date_=date(2026, 1, 1), type="BUY", quantity="15", price="600"),
            txn(2, date_=date(2026, 7, 15), type="DIVIDEND", quantity="15", price="8"),
        ]
    )
    assert pos.remaining_shares == Decimal("15")
    assert pos.remaining_cost == Decimal("9000")
    assert pos.total_dividends_received == Decimal("120")


def test_dividend_fee_and_tax_reduce_net_dividend():
    pos = replay_transactions(
        [
            txn(1, date_=date(2026, 1, 1), type="BUY", quantity="10", price="100"),
            txn(2, date_=date(2026, 6, 1), type="DIVIDEND", quantity="10", price="5", fee="2", tax="1"),
        ]
    )
    assert pos.total_dividends_received == Decimal("47")  # 50 - 2 - 1
    assert pos.total_fees_paid == Decimal("2")
    assert pos.total_tax_paid == Decimal("1")


# ---- Standalone FEE transactions ----------------------------------------------


def test_standalone_fee_transaction_does_not_affect_shares():
    pos = replay_transactions(
        [
            txn(1, date_=date(2026, 1, 1), type="BUY", quantity="10", price="100"),
            txn(2, date_=date(2026, 2, 1), type="FEE", quantity="1", price="200"),
        ]
    )
    assert pos.remaining_shares == Decimal("10")
    assert pos.remaining_cost == Decimal("1000")
    assert pos.total_fees_paid == Decimal("200")


# ---- CASH_DEPOSIT / CASH_WITHDRAWAL behave like BUY / SELL --------------------


def test_cash_deposit_and_withdrawal_behave_like_buy_and_sell():
    pos = replay_transactions(
        [
            txn(1, date_=date(2026, 1, 1), type="CASH_DEPOSIT", quantity="1000", price="1"),
            txn(2, date_=date(2026, 2, 1), type="CASH_WITHDRAWAL", quantity="400", price="1"),
        ]
    )
    assert pos.remaining_shares == Decimal("600")
    assert pos.remaining_cost == Decimal("600")
    assert pos.realized_pnl == Decimal("0")  # price constant at 1 -> no gain/loss


def test_manual_market_value_fund_deposit_convention():
    """A4: the Global ETF fund records deposits as CASH_DEPOSIT with
    quantity=amount, price=1, so invested capital tracks correctly even
    though market value later comes from a manual valuation, not this
    quantity."""
    pos = replay_transactions([txn(1, type="CASH_DEPOSIT", quantity="120000", price="1")])
    assert pos.remaining_shares == Decimal("120000")
    assert pos.remaining_cost == Decimal("120000")


# ---- Independence per (account_id, asset_id) ----------------------------------


def test_multiple_accounts_holding_same_asset_are_independent():
    txns = [
        txn(1, account_id=1, asset_id=99, type="BUY", quantity="10", price="100"),
        txn(2, account_id=2, asset_id=99, type="BUY", quantity="5", price="200"),
    ]
    positions = calculate_positions(txns)

    assert len(positions) == 2
    pos_account1 = positions[(1, 99)]
    pos_account2 = positions[(2, 99)]
    assert pos_account1.remaining_shares == Decimal("10")
    assert pos_account1.average_cost == Decimal("100")
    assert pos_account2.remaining_shares == Decimal("5")
    assert pos_account2.average_cost == Decimal("200")


def test_calculate_positions_groups_multiple_assets_and_accounts():
    txns = [
        txn(1, account_id=1, asset_id=1, type="BUY", quantity="10", price="100"),
        txn(2, account_id=1, asset_id=2, type="BUY", quantity="20", price="50"),
        txn(3, account_id=2, asset_id=1, type="BUY", quantity="7", price="30"),
    ]
    positions = calculate_positions(txns)
    assert set(positions.keys()) == {(1, 1), (1, 2), (2, 1)}


def test_replay_transactions_rejects_mixed_pairs():
    with pytest.raises(MixedPositionError):
        replay_transactions(
            [
                txn(1, account_id=1, asset_id=1, type="BUY", quantity="10", price="100"),
                txn(2, account_id=1, asset_id=2, type="BUY", quantity="10", price="100"),
            ]
        )
