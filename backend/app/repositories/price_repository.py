from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.price_history import PriceHistory


class PriceRepository:
    def __init__(self, db: Session):
        self.db = db

    def latest(self, asset_id: int) -> PriceHistory | None:
        stmt = select(PriceHistory).where(PriceHistory.asset_id == asset_id).order_by(PriceHistory.date.desc()).limit(1)
        return self.db.execute(stmt).scalar_one_or_none()

    def range(self, asset_id: int, start: date | None = None, end: date | None = None) -> list[PriceHistory]:
        stmt = select(PriceHistory).where(PriceHistory.asset_id == asset_id)
        if start is not None:
            stmt = stmt.where(PriceHistory.date >= start)
        if end is not None:
            stmt = stmt.where(PriceHistory.date <= end)
        stmt = stmt.order_by(PriceHistory.date)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_asset_and_date(self, asset_id: int, on_date: date) -> PriceHistory | None:
        stmt = select(PriceHistory).where(PriceHistory.asset_id == asset_id, PriceHistory.date == on_date)
        return self.db.execute(stmt).scalar_one_or_none()

    def upsert(self, asset_id: int, on_date: date, **fields) -> PriceHistory:
        """Re-ingesting the same (asset, date) updates the existing row in
        place instead of hitting the uq_price_history_asset_date constraint
        (Phase 5B validation requirement: duplicates behave as an upsert,
        not a silent failure)."""
        existing = self.get_by_asset_and_date(asset_id, on_date)
        if existing is None:
            row = PriceHistory(asset_id=asset_id, date=on_date, **fields)
            self.db.add(row)
            self.db.flush()
            return row
        for key, value in fields.items():
            setattr(existing, key, value)
        self.db.flush()
        return existing
