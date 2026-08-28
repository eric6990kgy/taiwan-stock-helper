"""Orchestrates transaction CRUD with two rules that only live here (never
duplicated into routes, never pushed down into the calculation engine):

  1. TWD-only currency (architecture decision A3) — a DB-independent
     business rule, not a CHECK constraint, so FX support can be added
     later without a migration.
  2. Every create/update/delete is validated by replaying the resulting
     transaction history through app.analytics — an edit that would make a
     later SELL exceed available shares is rejected immediately (as
     InsufficientSharesError) instead of silently corrupting derived
     holdings that only surface as wrong numbers on the Dashboard later.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.analytics.cost_basis import replay_transactions
from app.analytics.types import TransactionInput
from app.models.transaction import Transaction
from app.repositories.account_repository import AccountRepository
from app.repositories.asset_repository import AssetRepository
from app.repositories.transaction_repository import TransactionRepository
from app.services.exceptions import NotFoundError, UnsupportedCurrencyError

SUPPORTED_CURRENCIES = ("TWD",)


def _to_input(txn: Transaction) -> TransactionInput:
    return TransactionInput(
        id=txn.id,
        account_id=txn.account_id,
        asset_id=txn.asset_id,
        date=txn.date,
        type=txn.type,
        quantity=txn.quantity,
        price=txn.price,
        fee=txn.fee,
        tax=txn.tax,
    )


class TransactionService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = TransactionRepository(db)
        self.accounts = AccountRepository(db)
        self.assets = AssetRepository(db)

    def get(self, transaction_id: int) -> Transaction:
        txn = self.repo.get(transaction_id)
        if txn is None:
            raise NotFoundError(f"Transaction {transaction_id} not found.")
        return txn

    def list(self, **filters) -> list[Transaction]:
        return self.repo.list(**filters)

    def _validate_references(self, account_id: int, asset_id: int) -> None:
        if self.accounts.get(account_id) is None:
            raise NotFoundError(f"Account {account_id} not found.")
        if self.assets.get(asset_id) is None:
            raise NotFoundError(f"Asset {asset_id} not found.")

    def _validate_currency(self, currency: str) -> None:
        if currency not in SUPPORTED_CURRENCIES:
            raise UnsupportedCurrencyError(currency)

    def _validate_replay(self, account_id: int, asset_id: int, candidates: list[TransactionInput]) -> None:
        """Re-derives the position for this pair with the proposed change
        applied. Lets InsufficientSharesError propagate untouched — it's
        already a clear, typed error from app.analytics."""
        if not candidates:
            return
        replay_transactions(candidates)

    def create(
        self,
        *,
        account_id: int,
        asset_id: int,
        date,
        type,
        quantity,
        price,
        fee,
        tax,
        currency: str,
        note: str | None,
    ) -> Transaction:
        self._validate_references(account_id, asset_id)
        self._validate_currency(currency)

        existing = [_to_input(t) for t in self.repo.list(account_id=account_id, asset_id=asset_id, limit=100_000)]
        candidate = TransactionInput(
            id=max((t.id for t in existing), default=0) + 1,  # provisional id, only used for same-date ordering
            account_id=account_id,
            asset_id=asset_id,
            date=date,
            type=type,
            quantity=quantity,
            price=price,
            fee=fee,
            tax=tax,
        )
        self._validate_replay(account_id, asset_id, existing + [candidate])

        txn = self.repo.create(
            account_id=account_id,
            asset_id=asset_id,
            date=date,
            type=type,
            quantity=quantity,
            price=price,
            fee=fee,
            tax=tax,
            currency=currency,
            note=note,
        )
        self.db.commit()
        return txn

    def update(self, transaction_id: int, **fields) -> Transaction:
        txn = self.get(transaction_id)
        currency = fields.get("currency")
        if currency is not None:
            self._validate_currency(currency)

        others = [
            _to_input(t)
            for t in self.repo.list(account_id=txn.account_id, asset_id=txn.asset_id, limit=100_000)
            if t.id != txn.id
        ]
        merged = {
            "id": txn.id,
            "account_id": txn.account_id,
            "asset_id": txn.asset_id,
            "date": fields.get("date", txn.date),
            "type": fields.get("type", txn.type),
            "quantity": fields.get("quantity", txn.quantity),
            "price": fields.get("price", txn.price),
            "fee": fields.get("fee", txn.fee),
            "tax": fields.get("tax", txn.tax),
        }
        candidate = TransactionInput(**merged)
        self._validate_replay(txn.account_id, txn.asset_id, others + [candidate])

        self.repo.update(txn, **fields)
        self.db.commit()
        return txn

    def delete(self, transaction_id: int) -> None:
        txn = self.get(transaction_id)
        remaining = [
            _to_input(t)
            for t in self.repo.list(account_id=txn.account_id, asset_id=txn.asset_id, limit=100_000)
            if t.id != txn.id
        ]
        self._validate_replay(txn.account_id, txn.asset_id, remaining)

        self.repo.delete(txn)
        self.db.commit()
