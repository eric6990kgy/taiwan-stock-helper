from sqlalchemy.orm import Session

from app.models.account import Account
from app.repositories.account_repository import AccountRepository
from app.repositories.transaction_repository import TransactionRepository
from app.services.exceptions import NotFoundError
from app.services.user_context import get_current_user_id


class AccountService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AccountRepository(db)
        self.transactions_repo = TransactionRepository(db)

    def get(self, account_id: int) -> Account:
        account = self.repo.get(account_id)
        if account is None:
            raise NotFoundError(f"Account {account_id} not found.")
        return account

    def list(self) -> list[Account]:
        return self.repo.list()

    def create(self, *, name: str, account_type: str, currency: str) -> Account:
        user_id = get_current_user_id(self.db)
        account = self.repo.create(user_id=user_id, name=name, account_type=account_type, currency=currency)
        self.db.commit()
        return account

    def update(self, account_id: int, **fields) -> Account:
        account = self.get(account_id)
        self.repo.update(account, **fields)
        self.db.commit()
        return account

    def delete(self, account_id: int) -> None:
        account = self.get(account_id)
        # Account.transactions carries an ORM-level `cascade="all,
        # delete-orphan"` (needed so removing a transaction from the
        # collection in memory deletes it) -- left unguarded, that same
        # cascade means deleting the account silently deletes every
        # transaction under it too, with no way back. Financial transaction
        # history must never be destroyed as a side effect of an unrelated
        # action, so this blocks the delete instead of letting the cascade
        # run; the caller must delete the account's transactions first.
        if self.transactions_repo.list(account_id=account_id, limit=1):
            raise ValueError(
                f"Cannot delete account {account_id!r}: it still has transactions. "
                "Delete its transactions first, or reassign them to another account."
            )
        self.repo.delete(account)
        self.db.commit()
