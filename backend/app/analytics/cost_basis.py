"""Transaction replay: the only place holdings, average cost, and realized
P&L are computed. Positions are never stored — every read replays the full
transaction history for a (account_id, asset_id) pair (Principle 2, A2).

Weighted-average cost (V1's only method — A1). On BUY/CASH_DEPOSIT, cost
basis and average cost update immediately. On SELL/CASH_WITHDRAWAL, shares
are removed at the *current* average cost (unaffected by earlier sells,
only by earlier buys), realizing P&L on the difference between proceeds and
that cost. DIVIDEND and FEE never touch shares or cost basis.
"""

from decimal import Decimal

from app.analytics.exceptions import InsufficientSharesError, MixedPositionError
from app.analytics.types import DECREASE_TYPES, INCREASE_TYPES, Position, TransactionInput


def empty_position(account_id: int, asset_id: int) -> Position:
    """A position with no transaction history — e.g. a watchlist stock never
    bought, or an account/asset pair with no activity yet."""
    return Position(account_id=account_id, asset_id=asset_id)


def _apply(position: Position, txn: TransactionInput) -> None:
    if txn.type in INCREASE_TYPES:
        cost_added = txn.quantity * txn.price + txn.fee
        position.remaining_cost += cost_added
        position.remaining_shares += txn.quantity
        position.average_cost = position.remaining_cost / position.remaining_shares
        position.total_fees_paid += txn.fee
        position.total_tax_paid += txn.tax

    elif txn.type in DECREASE_TYPES:
        if txn.quantity > position.remaining_shares:
            raise InsufficientSharesError(
                account_id=position.account_id,
                asset_id=position.asset_id,
                requested=txn.quantity,
                available=position.remaining_shares,
                transaction_date=txn.date,
            )
        proceeds = txn.quantity * txn.price - txn.fee - txn.tax
        cost_of_sold = txn.quantity * position.average_cost
        position.realized_pnl += proceeds - cost_of_sold
        position.remaining_cost -= cost_of_sold
        position.remaining_shares -= txn.quantity
        if position.remaining_shares == 0:
            # Snap to exactly zero rather than carrying Decimal rounding dust
            # from repeated average-cost division.
            position.remaining_cost = Decimal("0")
        position.total_fees_paid += txn.fee
        position.total_tax_paid += txn.tax

    elif txn.type == "DIVIDEND":
        net = txn.quantity * txn.price - txn.fee - txn.tax
        position.total_dividends_received += net
        position.total_fees_paid += txn.fee
        position.total_tax_paid += txn.tax

    elif txn.type == "FEE":
        # A standalone expense (e.g. custody/platform fee) not tied to a
        # buy or sell leg. Does not affect shares or cost basis.
        position.total_fees_paid += txn.quantity * txn.price + txn.fee
        position.total_tax_paid += txn.tax

    else:  # pragma: no cover - TransactionInput.__post_init__ already guards this
        raise ValueError(f"Unhandled transaction type: {txn.type!r}")

    position.transaction_count += 1


def replay_transactions(transactions: list[TransactionInput]) -> Position:
    """Replays one (account_id, asset_id) pair's full transaction history in
    chronological order (date, then id as a same-date tiebreaker — id is
    assumed to reflect insertion/entry order) and returns the resulting
    Position. Backdated transactions are handled correctly because sorting
    happens here, not by relying on caller order.

    Raises MixedPositionError if given transactions from more than one pair.
    Raises ValueError if given an empty list — use empty_position() for a
    pair with no transaction history.
    """
    if not transactions:
        raise ValueError("replay_transactions() requires at least one transaction; use empty_position() instead.")

    pairs = {(t.account_id, t.asset_id) for t in transactions}
    if len(pairs) > 1:
        raise MixedPositionError(pairs)

    account_id, asset_id = next(iter(pairs))
    position = empty_position(account_id, asset_id)

    for txn in sorted(transactions, key=lambda t: (t.date, t.id)):
        _apply(position, txn)

    return position


def calculate_positions(transactions: list[TransactionInput]) -> dict[tuple[int, int], Position]:
    """Groups transactions by (account_id, asset_id) and replays each group
    independently (architecture decision A2 — never a single global position
    per asset)."""
    groups: dict[tuple[int, int], list[TransactionInput]] = {}
    for txn in transactions:
        groups.setdefault((txn.account_id, txn.asset_id), []).append(txn)

    return {key: replay_transactions(txns) for key, txns in groups.items()}
