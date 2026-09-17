from datetime import date

from sqlalchemy.orm import Session

from app.repositories.asset_repository import AssetRepository
from app.repositories.journal_repository import JournalRepository
from app.schemas.journal import JournalEntryRead
from app.services.exceptions import NotFoundError


class JournalService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = JournalRepository(db)
        self.assets = AssetRepository(db)

    def _to_read(self, entry) -> JournalEntryRead:
        asset = self.assets.get(entry.asset_id) if entry.asset_id is not None else None
        return JournalEntryRead(
            id=entry.id,
            entry_date=entry.entry_date,
            category=entry.category,
            asset_id=entry.asset_id,
            ticker=asset.ticker if asset is not None else None,
            asset_name=asset.name if asset is not None else None,
            recommendation_id=entry.recommendation_id,
            body=entry.body,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )

    def list(
        self,
        asset_id: int | None = None,
        category: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[JournalEntryRead]:
        return [
            self._to_read(e)
            for e in self.repo.list(asset_id=asset_id, category=category, date_from=date_from, date_to=date_to)
        ]

    def get(self, entry_id: int) -> JournalEntryRead:
        entry = self.repo.get(entry_id)
        if entry is None:
            raise NotFoundError(f"Journal entry {entry_id} not found.")
        return self._to_read(entry)

    def create(self, **fields) -> JournalEntryRead:
        if fields.get("asset_id") is not None and self.assets.get(fields["asset_id"]) is None:
            raise NotFoundError(f"Asset {fields['asset_id']} not found.")
        entry = self.repo.create(**fields)
        self.db.commit()
        return self._to_read(entry)

    def update(self, entry_id: int, **fields) -> JournalEntryRead:
        entry = self.repo.get(entry_id)
        if entry is None:
            raise NotFoundError(f"Journal entry {entry_id} not found.")
        self.repo.update(entry, **fields)
        self.db.commit()
        return self._to_read(entry)

    def delete(self, entry_id: int) -> None:
        entry = self.repo.get(entry_id)
        if entry is None:
            raise NotFoundError(f"Journal entry {entry_id} not found.")
        self.repo.delete(entry)
        self.db.commit()
