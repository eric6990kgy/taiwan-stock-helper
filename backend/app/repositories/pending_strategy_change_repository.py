from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.pending_strategy_change import PendingStrategyChange


class PendingStrategyChangeRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, change_id: int) -> PendingStrategyChange | None:
        return self.db.get(PendingStrategyChange, change_id)

    def list(self, status: str | None = None) -> list[PendingStrategyChange]:
        stmt = select(PendingStrategyChange)
        if status is not None:
            stmt = stmt.where(PendingStrategyChange.status == status)
        stmt = stmt.order_by(PendingStrategyChange.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def create(self, **fields) -> PendingStrategyChange:
        row = PendingStrategyChange(**fields)
        self.db.add(row)
        self.db.flush()
        return row

    def update(self, row: PendingStrategyChange, **fields) -> PendingStrategyChange:
        for key, value in fields.items():
            setattr(row, key, value)
        self.db.flush()
        return row
