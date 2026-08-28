"""Plain data structures shared by the calculation engine. No ORM, no
Pydantic — these are what keep the engine importable without FastAPI or
SQLAlchemy on the path.
"""

from dataclasses import dataclass
from datetime import date as date_
from decimal import Decimal

TRANSACTION_TYPES = ("BUY", "SELL", "DIVIDEND", "FEE", "CASH_DEPOSIT", "CASH_WITHDRAWAL")

# Economically, a CASH_DEPOSIT behaves like a BUY (adds quantity + cost basis)
# and a CASH_WITHDRAWAL behaves like a SELL (removes quantity, realizes P&L)
# — this covers both ordinary cash accounts and the MANUAL_MARKET_VALUE
# convention where a fund's principal contributions are recorded as
# CASH_DEPOSIT with quantity=amount, price=1 (architecture decision A4).
INCREASE_TYPES = ("BUY", "CASH_DEPOSIT")
DECREASE_TYPES = ("SELL", "CASH_WITHDRAWAL")


@dataclass(frozen=True)
class TransactionInput:
    """Mirrors the `transactions` table (Phase 1), decoupled from the ORM row."""

    id: int
    account_id: int
    asset_id: int
    date: date_
    type: str
    quantity: Decimal
    price: Decimal
    fee: Decimal = Decimal("0")
    tax: Decimal = Decimal("0")

    def __post_init__(self):
        if self.type not in TRANSACTION_TYPES:
            raise ValueError(f"Unknown transaction type: {self.type!r}")


@dataclass
class Position:
    """The derived state of one (account_id, asset_id) pair after replaying
    its transaction history in chronological order. Never stored directly —
    always recomputed from transactions (Principle 2)."""

    account_id: int
    asset_id: int
    remaining_shares: Decimal = Decimal("0")
    average_cost: Decimal = Decimal("0")
    remaining_cost: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")
    total_dividends_received: Decimal = Decimal("0")
    total_fees_paid: Decimal = Decimal("0")
    total_tax_paid: Decimal = Decimal("0")
    transaction_count: int = 0


@dataclass
class ValuedPosition:
    """A Position combined with a current price into market value / P&L."""

    position: Position
    latest_close: Decimal
    valuation_method: str
    market_value: Decimal
    unrealized_pnl: Decimal
    return_pct: Decimal | None
