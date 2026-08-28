"""DB access only — no business rules. Services own validation/orchestration."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.account import Account


class AccountRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, account_id: int) -> Account | None:
        return self.db.get(Account, account_id)

    def list(self) -> list[Account]:
        return list(self.db.execute(select(Account)).scalars().all())

    def create(self, **fields) -> Account:
        account = Account(**fields)
        self.db.add(account)
        self.db.flush()
        return account

    def update(self, account: Account, **fields) -> Account:
        for key, value in fields.items():
            if value is not None:
                setattr(account, key, value)
        self.db.flush()
        return account

    def delete(self, account: Account) -> None:
        self.db.delete(account)
        self.db.flush()
