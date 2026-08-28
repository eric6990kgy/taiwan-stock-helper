from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.repositories.asset_repository import AssetRepository
from app.repositories.watchlist_repository import WatchlistRepository
from app.schemas.watchlist import WatchlistRead
from app.services.exceptions import DuplicateError, NotFoundError


class WatchlistService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = WatchlistRepository(db)
        self.assets = AssetRepository(db)

    def _to_read(self, entry) -> WatchlistRead:
        asset = self.assets.get(entry.asset_id)
        return WatchlistRead(
            id=entry.id,
            asset_id=entry.asset_id,
            ticker=asset.ticker,
            asset_name=asset.name,
            status=entry.status,
            reason=entry.reason,
            target_metrics=entry.target_metrics,
            entry_consideration=entry.entry_consideration,
            review_date=entry.review_date,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )

    def list(self, status: str | None = None) -> list[WatchlistRead]:
        return [self._to_read(e) for e in self.repo.list(status=status)]

    def get(self, watchlist_id: int) -> WatchlistRead:
        entry = self.repo.get(watchlist_id)
        if entry is None:
            raise NotFoundError(f"Watchlist entry {watchlist_id} not found.")
        return self._to_read(entry)

    def create(self, **fields) -> WatchlistRead:
        if self.assets.get(fields["asset_id"]) is None:
            raise NotFoundError(f"Asset {fields['asset_id']} not found.")
        try:
            entry = self.repo.create(**fields)
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise DuplicateError(f"Asset {fields['asset_id']} is already on the watchlist.") from exc
        return self._to_read(entry)

    def update(self, watchlist_id: int, **fields) -> WatchlistRead:
        entry = self.repo.get(watchlist_id)
        if entry is None:
            raise NotFoundError(f"Watchlist entry {watchlist_id} not found.")
        self.repo.update(entry, **fields)
        self.db.commit()
        return self._to_read(entry)

    def delete(self, watchlist_id: int) -> None:
        entry = self.repo.get(watchlist_id)
        if entry is None:
            raise NotFoundError(f"Watchlist entry {watchlist_id} not found.")
        self.repo.delete(entry)
        self.db.commit()
