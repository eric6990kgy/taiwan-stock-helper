from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

STRATEGY_VERSION_STATUSES = ("ACTIVE", "SUPERSEDED", "ROLLED_BACK")
STRATEGY_CHANGE_TYPES = ("AUTO_APPLIED", "CONFIRMED")


class StrategyVersion(Base):
    """One versioned, auditable snapshot of the signal-engine's tunable
    parameters (Phase 8, 個股訊號引擎規格書 Phase B). `rules` is a
    SignalRules.to_dict() -- a flat, JSON-serializable parameter set, never
    the regime-weight tables (those are Phase 7's own composite-scoring
    concern, not this versioning layer).

    Exactly one row has status=ACTIVE at any time -- enforced in
    StrategyService, not a DB constraint (same "service layer owns the
    invariant" convention as TWD-only/insufficient-shares checks
    elsewhere), since SQLite CHECK constraints can't express "at most one
    row where X" across the table.
    """

    __tablename__ = "strategy_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    rules: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    change_type: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Walk-forward hit-rate backtest (app.analytics.signal_backtest), run
    # against this version's rules at creation time. Both null means no
    # price history was available yet to backtest against -- never a
    # fabricated rate.
    backtest_hit_rate: Mapped[Numeric | None] = mapped_column(Numeric(5, 4), nullable=True)
    backtest_n: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        CheckConstraint(f"status IN {STRATEGY_VERSION_STATUSES}", name="ck_strategy_versions_status"),
        CheckConstraint(f"change_type IN {STRATEGY_CHANGE_TYPES}", name="ck_strategy_versions_change_type"),
        UniqueConstraint("version_number", name="uq_strategy_versions_version_number"),
    )
