from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

AGENT_ROLES = ("FUNDAMENTAL_ANALYST", "TECHNICAL_ANALYST", "PORTFOLIO_MANAGER")
# Reuses Signal's own vocabulary (app.analytics.signal_types) -- UNAVAILABLE
# is for "my own inputs are too sparse to have a real view", same "missing
# data != a fabricated reading" principle, never a system decision (Phase 12).
AGENT_CALLS = ("BULLISH", "BEARISH", "NEUTRAL", "UNAVAILABLE")


class AgentAnalysis(Base):
    """One Gemini agent's narrative research opinion on a Recommendation
    (Phase 12) -- rides alongside the deterministic Phase 8 decision,
    never replaces it. Up to 3 rows per recommendation, one per role.
    `call` is scored against RecommendationOutcome.actual_direction the
    same way the deterministic engine's call already is (see
    AgentPerformanceService) -- no separate scoring pass, no fabricated
    KPI number."""

    __tablename__ = "agent_analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    recommendation_id: Mapped[int] = mapped_column(ForeignKey("recommendations.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    call: Mapped[str] = mapped_column(String(15), nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    # A handful of short (one-sentence), labeled fields specific to that
    # role -- e.g. {"revenue_trend": ..., "profitability": ..., ...} for
    # FUNDAMENTAL_ANALYST -- not a free-text paragraph (the field set
    # differs per role, hence JSON rather than fixed columns; see
    # AgentResearchService's per-role Pydantic schemas for the exact keys).
    details: Mapped[dict] = mapped_column(JSON, nullable=False)
    model: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    recommendation: Mapped["Recommendation"] = relationship(back_populates="agent_analyses")

    __table_args__ = (
        CheckConstraint(f"role IN {AGENT_ROLES}", name="ck_agent_analyses_role"),
        CheckConstraint(f"call IN {AGENT_CALLS}", name="ck_agent_analyses_call"),
        UniqueConstraint("recommendation_id", "role", name="uq_agent_analyses_recommendation_role"),
    )
