from datetime import date as date_, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

DIRECTIONS = ("BULLISH", "BEARISH", "NEUTRAL")


class RecommendationOutcome(Base):
    """Ground-truth label for a past Recommendation (Phase 10) -- did the
    price actually move the direction the recommendation's new_status
    called, `horizon_trading_days` trading days later? One row per
    Recommendation (recommendation_id is unique), created only once enough
    future price history exists to score it -- absence of a row means
    "not due yet", never a fabricated/null placeholder (see
    RecommendationOutcomeService.score_due_outcomes)."""

    __tablename__ = "recommendation_outcomes"

    id: Mapped[int] = mapped_column(primary_key=True)
    recommendation_id: Mapped[int] = mapped_column(ForeignKey("recommendations.id"), nullable=False, unique=True)
    horizon_trading_days: Mapped[int] = mapped_column(Integer, nullable=False)
    as_of_date: Mapped[date_] = mapped_column(Date, nullable=False)
    outcome_date: Mapped[date_] = mapped_column(Date, nullable=False)
    from_close: Mapped[Numeric] = mapped_column(Numeric(18, 4), nullable=False)
    to_close: Mapped[Numeric] = mapped_column(Numeric(18, 4), nullable=False)
    actual_direction: Mapped[str] = mapped_column(String(10), nullable=False)
    hit: Mapped[bool] = mapped_column(Boolean, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    recommendation: Mapped["Recommendation"] = relationship(back_populates="outcome")

    __table_args__ = (
        CheckConstraint(f"actual_direction IN {DIRECTIONS}", name="ck_recommendation_outcomes_actual_direction"),
    )
