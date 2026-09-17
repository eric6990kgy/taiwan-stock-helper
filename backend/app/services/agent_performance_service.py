"""Per-role KPI for the Gemini multi-agent research team (Phase 12) --
reuses Phase 10's already-scored RecommendationOutcome data entirely, no
new scoring pass. An AgentAnalysis's `call` is graded against the same
`actual_direction` the deterministic engine's call was already graded
against on that same recommendation.
"""

from sqlalchemy.orm import Session

from app.repositories.agent_analysis_repository import AgentAnalysisRepository
from app.schemas.review import ReviewSummaryRead
from app.services.recommendation_outcome_service import ReviewSummary


class AgentPerformanceService:
    def __init__(self, db: Session):
        self.repo = AgentAnalysisRepository(db)

    def get_summary(self, role: str | None = None) -> ReviewSummary:
        pairs = self.repo.list_scored(role=role)
        hits = sum(1 for analysis, outcome in pairs if analysis.call == outcome.actual_direction)
        return ReviewSummary(hits=hits, n=len(pairs))

    def get_summary_read(self, role: str | None = None) -> ReviewSummaryRead:
        summary = self.get_summary(role=role)
        return ReviewSummaryRead(
            hits=summary.hits, n=summary.n, hit_rate=str(summary.hit_rate) if summary.hit_rate is not None else None
        )
