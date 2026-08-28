from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Fundamentals(Base):
    """One row per (asset, period). period is a free-form label ('2024',
    '2025Q2', 'TTM') rather than a strict date, since annual/quarterly/TTM
    reporting cadences differ. Every metric must carry `source` and
    `last_updated` (Principle 5) — the row-level fields already do."""

    __tablename__ = "fundamentals"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False)
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    revenue: Mapped[Numeric | None] = mapped_column(Numeric(20, 4), nullable=True)
    eps: Mapped[Numeric | None] = mapped_column(Numeric(18, 4), nullable=True)
    gross_margin: Mapped[Numeric | None] = mapped_column(Numeric(9, 4), nullable=True)
    operating_margin: Mapped[Numeric | None] = mapped_column(Numeric(9, 4), nullable=True)
    net_margin: Mapped[Numeric | None] = mapped_column(Numeric(9, 4), nullable=True)
    roe: Mapped[Numeric | None] = mapped_column(Numeric(9, 4), nullable=True)
    roa: Mapped[Numeric | None] = mapped_column(Numeric(9, 4), nullable=True)
    debt_ratio: Mapped[Numeric | None] = mapped_column(Numeric(9, 4), nullable=True)
    operating_cash_flow: Mapped[Numeric | None] = mapped_column(Numeric(20, 4), nullable=True)
    free_cash_flow: Mapped[Numeric | None] = mapped_column(Numeric(20, 4), nullable=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="MOCK")
    last_updated: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    asset: Mapped["Asset"] = relationship(back_populates="fundamentals")

    __table_args__ = (
        UniqueConstraint("asset_id", "period", name="uq_fundamentals_asset_period"),
    )
