from datetime import date as date_, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

WATCHLIST_STATUSES = ("WATCHING", "RESEARCHING", "CANDIDATE", "OWNED", "REJECTED")


class Watchlist(Base):
    """One active watchlist entry per asset (asset_id is unique) — editing an
    existing entry rather than accumulating duplicate rows per ticker."""

    __tablename__ = "watchlist"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="WATCHING")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    entry_consideration: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_date: Mapped[date_ | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    asset: Mapped["Asset"] = relationship(back_populates="watchlist_entry")

    __table_args__ = (
        CheckConstraint(f"status IN {WATCHLIST_STATUSES}", name="ck_watchlist_status"),
    )
