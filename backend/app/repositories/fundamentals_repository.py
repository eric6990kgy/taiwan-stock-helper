from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.fundamentals import Fundamentals


class FundamentalsRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_asset(self, asset_id: int) -> list[Fundamentals]:
        stmt = select(Fundamentals).where(Fundamentals.asset_id == asset_id).order_by(Fundamentals.period)
        return list(self.db.execute(stmt).scalars().all())

    def latest_ttm(self, asset_id: int) -> Fundamentals | None:
        stmt = select(Fundamentals).where(Fundamentals.asset_id == asset_id, Fundamentals.period == "TTM")
        return self.db.execute(stmt).scalar_one_or_none()
