from datetime import date as date_, datetime

from sqlalchemy import JSON, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

RECOMMENDATION_ACTIONS = ("WATCH", "CONSIDER_INCREASE", "CONSIDER_DECREASE")


class Recommendation(Base):
    """One row per (asset, scan run) whose signal status changed (Phase 8).
    Never a BUY/SELL instruction -- `action` is conditional language only
    (關注/考慮增加關注度/考慮減碼), same principle as Signal itself.

    `risk_blocked`/`risk_block_reason` are the whole point of this phase:
    every CONSIDER_INCREASE is checked against Phase A's risk/drawdown gate
    *before* this row is created, never after (個股訊號引擎規格書 Phase B
    Sec.02 目標3) -- see RecommendationService.run_daily_scan().
    """

    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False)
    strategy_version_id: Mapped[int] = mapped_column(ForeignKey("strategy_versions.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    previous_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    # A JSON snapshot of the non-neutral Signals that drove this
    # recommendation (id/status/explanation) -- so "why did this fire" has
    # an answer even after the underlying data changes on a later scan.
    triggered_signals: Mapped[list] = mapped_column(JSON, nullable=False)
    risk_blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    risk_block_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # A snapshot of the composite score/regime at the moment this fired --
    # not a live read, same "why did this fire has an answer even after
    # the underlying data changes" rationale as triggered_signals above.
    composite_score: Mapped[Numeric | None] = mapped_column(Numeric(5, 2), nullable=True)
    regime: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # The real trading date the signal was computed from (SignalResult.as_of)
    # -- NOT the same as created_at, which is just whenever "Update Market
    # Data" happened to run (Phase 10). Nullable because rows created before
    # this column existed have no value; RecommendationOutcomeService falls
    # back to the nearest price_history date at-or-before created_at for those.
    as_of_date: Mapped[date_ | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    asset: Mapped["Asset"] = relationship(back_populates="recommendations")
    outcome: Mapped["RecommendationOutcome"] = relationship(back_populates="recommendation", uselist=False)
    agent_analyses: Mapped[list["AgentAnalysis"]] = relationship(back_populates="recommendation")

    __table_args__ = (CheckConstraint(f"action IN {RECOMMENDATION_ACTIONS}", name="ck_recommendations_action"),)
