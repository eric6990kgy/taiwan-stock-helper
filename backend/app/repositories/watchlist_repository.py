from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.watchlist import Watchlist


class WatchlistRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, watchlist_id: int) -> Watchlist | None:
        return self.db.get(Watchlist, watchlist_id)

    def get_by_asset(self, asset_id: int) -> Watchlist | None:
        return self.db.execute(select(Watchlist).where(Watchlist.asset_id == asset_id)).scalar_one_or_none()

    def list(self, status: str | None = None) -> list[Watchlist]:
        stmt = select(Watchlist)
        if status is not None:
            stmt = stmt.where(Watchlist.status == status)
        return list(self.db.execute(stmt).scalars().all())

    def create(self, **fields) -> Watchlist:
        entry = Watchlist(**fields)
        self.db.add(entry)
        self.db.flush()
        return entry

    def update(self, entry: Watchlist, **fields) -> Watchlist:
        for key, value in fields.items():
            if value is not None:
                setattr(entry, key, value)
        self.db.flush()
        return entry

    def delete(self, entry: Watchlist) -> None:
        self.db.delete(entry)
        self.db.flush()
