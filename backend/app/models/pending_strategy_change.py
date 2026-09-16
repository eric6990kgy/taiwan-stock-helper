from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

PENDING_STRATEGY_CHANGE_STATUSES = ("PENDING", "CONFIRMED", "REJECTED")


class PendingStrategyChange(Base):
    """A "big" strategy change (added/removed signal parameter, per
    StrategyService's small-vs-big rule) awaiting explicit user
    confirmation (個股訊號引擎規格書 Phase B Sec.05 P0 "待確認佇列") --
    never auto-applied, never silently expires. `backtest_before`/`_after`
    are BacktestResult snapshots (app.analytics.signal_backtest) so the
    user can compare hit rates before deciding.
    """

    __tablename__ = "pending_strategy_changes"

    id: Mapped[int] = mapped_column(primary_key=True)
    proposed_rules: Mapped[dict] = mapped_column(JSON, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    backtest_before: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    backtest_after: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint(f"status IN {PENDING_STRATEGY_CHANGE_STATUSES}", name="ck_pending_strategy_changes_status"),
    )
