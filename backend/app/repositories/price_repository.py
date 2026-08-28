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
