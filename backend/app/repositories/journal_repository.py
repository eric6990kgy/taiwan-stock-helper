from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.journal_entry import JournalEntry


class JournalRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, entry_id: int) -> JournalEntry | None:
        return self.db.get(JournalEntry, entry_id)

    def list(
        self,
        asset_id: int | None = None,
        category: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[JournalEntry]:
        stmt = select(JournalEntry)
        if asset_id is not None:
            stmt = stmt.where(JournalEntry.asset_id == asset_id)
        if category is not None:
            stmt = stmt.where(JournalEntry.category == category)
        if date_from is not None:
            stmt = stmt.where(JournalEntry.entry_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(JournalEntry.entry_date <= date_to)
        stmt = stmt.order_by(JournalEntry.entry_date.desc(), JournalEntry.id.desc())
        return list(self.db.execute(stmt).scalars().all())

    def create(self, **fields) -> JournalEntry:
        entry = JournalEntry(**fields)
        self.db.add(entry)
        self.db.flush()
        return entry

    def update(self, entry: JournalEntry, **fields) -> JournalEntry:
        for key, value in fields.items():
            if value is not None:
                setattr(entry, key, value)
        self.db.flush()
        return entry

    def delete(self, entry: JournalEntry) -> None:
        self.db.delete(entry)
        self.db.flush()
