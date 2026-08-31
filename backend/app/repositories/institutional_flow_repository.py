from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.institutional_flow import InstitutionalFlow


class InstitutionalFlowRepository:
    def __init__(self, db: Session):
        self.db = db

    def range(self, asset_id: int, start: date | None = None, end: date | None = None) -> list[InstitutionalFlow]:
        stmt = select(InstitutionalFlow).where(InstitutionalFlow.asset_id == asset_id)
        if start is not None:
            stmt = stmt.where(InstitutionalFlow.date >= start)
        if end is not None:
            stmt = stmt.where(InstitutionalFlow.date <= end)
        stmt = stmt.order_by(InstitutionalFlow.date)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_asset_and_date(self, asset_id: int, on_date: date) -> InstitutionalFlow | None:
        stmt = select(InstitutionalFlow).where(InstitutionalFlow.asset_id == asset_id, InstitutionalFlow.date == on_date)
        return self.db.execute(stmt).scalar_one_or_none()

    def upsert(self, asset_id: int, on_date: date, **fields) -> InstitutionalFlow:
        existing = self.get_by_asset_and_date(asset_id, on_date)
        if existing is None:
            row = InstitutionalFlow(asset_id=asset_id, date=on_date, **fields)
            self.db.add(row)
            self.db.flush()
            return row
        for key, value in fields.items():
            setattr(existing, key, value)
        self.db.flush()
        return existing
