class InsufficientSharesError(ValueError):
    """Raised when a SELL/CASH_WITHDRAWAL transaction requests more quantity
    than the position currently holds at that point in the chronological
    replay. Carries enough detail to surface a clear error to the user
    (PRD Sec.39 — no bare "something went wrong")."""

    def __init__(self, account_id: int, asset_id: int, requested, available, transaction_date):
        self.account_id = account_id
        self.asset_id = asset_id
        self.requested = requested
        self.available = available
        self.transaction_date = transaction_date
        super().__init__(
            f"Cannot sell {requested} units of asset {asset_id} in account {account_id} on "
            f"{transaction_date}: only {available} available at that point in the transaction history."
        )


class MixedPositionError(ValueError):
    """Raised when replay_transactions() is given transactions spanning more
    than one (account_id, asset_id) pair — positions must always be computed
    independently per pair (architecture decision A2)."""

    def __init__(self, pairs):
        self.pairs = pairs
        super().__init__(
            f"replay_transactions() requires all transactions to share one (account_id, asset_id) "
            f"pair; got {sorted(pairs)}. Use calculate_positions() to process multiple pairs at once."
        )
