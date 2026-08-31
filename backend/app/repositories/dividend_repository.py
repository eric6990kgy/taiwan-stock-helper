from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dividend import Dividend


class DividendRepository:
    def __init__(self, db: Session):
        self.db = db

    def range(self, asset_id: int, start: date | None = None, end: date | None = None) -> list[Dividend]:
        stmt = select(Dividend).where(Dividend.asset_id == asset_id)
        if start is not None:
            stmt = stmt.where(Dividend.ex_dividend_date >= start)
        if end is not None:
            stmt = stmt.where(Dividend.ex_dividend_date <= end)
        stmt = stmt.order_by(Dividend.ex_dividend_date)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_asset_and_date(self, asset_id: int, ex_dividend_date: date) -> Dividend | None:
        stmt = select(Dividend).where(Dividend.asset_id == asset_id, Dividend.ex_dividend_date == ex_dividend_date)
        return self.db.execute(stmt).scalar_one_or_none()

    def upsert(self, asset_id: int, ex_dividend_date: date, **fields) -> Dividend:
        """One row per (asset, ex_dividend_date) -- re-ingesting the same
        dividend event updates it in place rather than creating a duplicate
        (Phase 5B validation requirement: duplicates behave as an upsert)."""
        existing = self.get_by_asset_and_date(asset_id, ex_dividend_date)
        if existing is None:
            row = Dividend(asset_id=asset_id, ex_dividend_date=ex_dividend_date, **fields)
            self.db.add(row)
            self.db.flush()
            return row
        for key, value in fields.items():
            setattr(existing, key, value)
        self.db.flush()
        return existing
