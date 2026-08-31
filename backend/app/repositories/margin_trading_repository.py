from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.margin_trading import MarginTrading


class MarginTradingRepository:
    def __init__(self, db: Session):
        self.db = db

    def range(self, asset_id: int, start: date | None = None, end: date | None = None) -> list[MarginTrading]:
        stmt = select(MarginTrading).where(MarginTrading.asset_id == asset_id)
        if start is not None:
            stmt = stmt.where(MarginTrading.date >= start)
        if end is not None:
            stmt = stmt.where(MarginTrading.date <= end)
        stmt = stmt.order_by(MarginTrading.date)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_asset_and_date(self, asset_id: int, on_date: date) -> MarginTrading | None:
        stmt = select(MarginTrading).where(MarginTrading.asset_id == asset_id, MarginTrading.date == on_date)
        return self.db.execute(stmt).scalar_one_or_none()

    def upsert(self, asset_id: int, on_date: date, **fields) -> MarginTrading:
        existing = self.get_by_asset_and_date(asset_id, on_date)
        if existing is None:
            row = MarginTrading(asset_id=asset_id, date=on_date, **fields)
            self.db.add(row)
            self.db.flush()
            return row
        for key, value in fields.items():
            setattr(existing, key, value)
        self.db.flush()
        return existing
