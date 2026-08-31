from datetime import date as date_
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Date, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class MonthlyRevenue(Base):
    """One row per (asset, revenue_year, revenue_month) -- keyed by the
    *covered* month, not the announcement date (see MonthlyRevenueDTO's
    docstring). `announcement_date` keeps FinMind's raw `date` field for
    reference only; it is never the natural key. Raw fact only -- YoY/MoM
    growth is computed on read (app/services), never persisted here.
    """

    __tablename__ = "monthly_revenue"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False)
    revenue_year: Mapped[int] = mapped_column(nullable=False)
    revenue_month: Mapped[int] = mapped_column(nullable=False)
    revenue: Mapped[Numeric] = mapped_column(Numeric(24, 4), nullable=False)
    announcement_date: Mapped[date_ | None] = mapped_column(Date, nullable=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="MOCK")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    asset: Mapped["Asset"] = relationship(back_populates="monthly_revenues")

    __table_args__ = (
        UniqueConstraint("asset_id", "revenue_year", "revenue_month", name="uq_monthly_revenue_asset_period"),
        CheckConstraint("revenue_month >= 1 AND revenue_month <= 12", name="ck_monthly_revenue_month_range"),
    )
