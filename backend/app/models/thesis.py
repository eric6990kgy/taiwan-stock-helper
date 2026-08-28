from datetime import date as date_, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

THESIS_STATUSES = ("INTACT", "NEEDS_REVIEW", "BROKEN")


class InvestmentThesis(Base):
    """One thesis per asset. key_metrics is a structured list of
    {label, operator, value} objects (not free text) so a future AI reviewer
    can actually evaluate them against fundamentals, per Principle 6 (AI must
    separate fact/analysis/assumption from user decision, not issue verdicts)."""

    __tablename__ = "investment_thesis"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False, unique=True)
    thesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    catalysts: Mapped[str | None] = mapped_column(Text, nullable=True)
    risks: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_metrics: Mapped[list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="INTACT")
    last_reviewed: Mapped[date_ | None] = mapped_column(Date, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    asset: Mapped["Asset"] = relationship(back_populates="thesis")

    __table_args__ = (
        CheckConstraint(f"status IN {THESIS_STATUSES}", name="ck_thesis_status"),
    )
