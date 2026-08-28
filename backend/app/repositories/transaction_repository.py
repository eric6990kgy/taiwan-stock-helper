from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.transaction import Transaction


class TransactionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, transaction_id: int) -> Transaction | None:
        return self.db.get(Transaction, transaction_id)

    def list_all(self) -> list[Transaction]:
        """Every transaction, unfiltered — used by the portfolio service to
        feed the calculation engine (which does its own chronological sort).
        Defined before list() below: once a method literally named `list` is
        bound in this class's namespace, it shadows the builtin for every
        `list[...]` annotation that follows it in the class body."""
        return list(self.db.execute(select(Transaction)).scalars().all())

    def list(
        self,
        account_id: int | None = None,
        asset_id: int | None = None,
        type: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Transaction]:
        stmt = select(Transaction)
        if account_id is not None:
            stmt = stmt.where(Transaction.account_id == account_id)
        if asset_id is not None:
            stmt = stmt.where(Transaction.asset_id == asset_id)
        if type is not None:
            stmt = stmt.where(Transaction.type == type)
        if date_from is not None:
            stmt = stmt.where(Transaction.date >= date_from)
        if date_to is not None:
            stmt = stmt.where(Transaction.date <= date_to)
        stmt = stmt.order_by(Transaction.date, Transaction.id).limit(limit).offset(offset)
        return list(self.db.execute(stmt).scalars().all())

    def create(self, **fields) -> Transaction:
        txn = Transaction(**fields)
        self.db.add(txn)
        self.db.flush()
        return txn

    def update(self, txn: Transaction, **fields) -> Transaction:
        for key, value in fields.items():
            if value is not None:
                setattr(txn, key, value)
        self.db.flush()
        return txn

    def delete(self, txn: Transaction) -> None:
        self.db.delete(txn)
        self.db.flush()
