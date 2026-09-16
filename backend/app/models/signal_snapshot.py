from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class SignalSnapshot(Base):
    """The last known overall_status per asset (Phase 8) -- purely for the
    daily scan's change-detection ("only surface what changed", 個股訊號引擎規格書
    Phase B Sec.05 P0), not a history table. One row per asset, overwritten
    on every scan; RecommendationService diffs the new SignalResult's
    overall_status against this row before deciding whether to emit a
    Recommendation.
    """

    __tablename__ = "signal_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False)
    overall_status: Mapped[str] = mapped_column(String(20), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    asset: Mapped["Asset"] = relationship(back_populates="signal_snapshot")

    __table_args__ = (UniqueConstraint("asset_id", name="uq_signal_snapshots_asset_id"),)
