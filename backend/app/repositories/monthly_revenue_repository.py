from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.monthly_revenue import MonthlyRevenue


class MonthlyRevenueRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_asset(self, asset_id: int) -> list[MonthlyRevenue]:
        stmt = (
            select(MonthlyRevenue)
            .where(MonthlyRevenue.asset_id == asset_id)
            .order_by(MonthlyRevenue.revenue_year, MonthlyRevenue.revenue_month)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_by_asset_and_period(self, asset_id: int, revenue_year: int, revenue_month: int) -> MonthlyRevenue | None:
        stmt = select(MonthlyRevenue).where(
            MonthlyRevenue.asset_id == asset_id,
            MonthlyRevenue.revenue_year == revenue_year,
            MonthlyRevenue.revenue_month == revenue_month,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def upsert(self, asset_id: int, revenue_year: int, revenue_month: int, **fields) -> MonthlyRevenue:
        existing = self.get_by_asset_and_period(asset_id, revenue_year, revenue_month)
        if existing is None:
            row = MonthlyRevenue(asset_id=asset_id, revenue_year=revenue_year, revenue_month=revenue_month, **fields)
            self.db.add(row)
            self.db.flush()
            return row
        for key, value in fields.items():
            setattr(existing, key, value)
        self.db.flush()
        return existing
