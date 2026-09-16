from datetime import date as date_
from datetime import datetime

from sqlalchemy import DateTime, Date, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Score(Base):
    """One row per (asset, date) -- a persisted composite score snapshot
    (Phase 7), computed by app.analytics.scoring from that day's technical/
    fundamentals/valuation/regime data. Persisted (unlike Phase 6's
    on-demand technical indicators) so a future score-trend chart and any
    future weight-validation work has historical data to work from.

    Each *_score column and composite_score is nullable -- a sub-score that
    couldn't be computed (insufficient data) is None, never a fabricated
    neutral value; missing_components names exactly which ones, so the UI
    never has to guess why a score looks incomplete.
    """

    __tablename__ = "scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False)
    date: Mapped[date_] = mapped_column(Date, nullable=False)

    value_score: Mapped[Numeric | None] = mapped_column(Numeric(5, 2), nullable=True)
    growth_score: Mapped[Numeric | None] = mapped_column(Numeric(5, 2), nullable=True)
    momentum_score: Mapped[Numeric | None] = mapped_column(Numeric(5, 2), nullable=True)
    quality_score: Mapped[Numeric | None] = mapped_column(Numeric(5, 2), nullable=True)
    composite_score: Mapped[Numeric | None] = mapped_column(Numeric(5, 2), nullable=True)
    regime: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # Comma-joined sub-score names that came back None for this row (e.g.
    # "growth,quality"), empty string if all four were computable.
    missing_components: Mapped[str] = mapped_column(String(50), nullable=False, default="")

    source: Mapped[str] = mapped_column(String(30), nullable=False, default="CALCULATED")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    asset: Mapped["Asset"] = relationship(back_populates="scores")

    __table_args__ = (UniqueConstraint("asset_id", "date", name="uq_scores_asset_date"),)
