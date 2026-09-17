from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_analysis import AgentAnalysis
from app.models.recommendation import Recommendation
from app.models.recommendation_outcome import RecommendationOutcome


class AgentAnalysisRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_recommendation(self, recommendation_id: int) -> list[AgentAnalysis]:
        stmt = select(AgentAnalysis).where(AgentAnalysis.recommendation_id == recommendation_id)
        return list(self.db.execute(stmt).scalars().all())

    def create(self, **fields) -> AgentAnalysis:
        row = AgentAnalysis(**fields)
        self.db.add(row)
        self.db.flush()
        return row

    def list_scored(self, role: str | None = None) -> list[tuple[AgentAnalysis, RecommendationOutcome]]:
        """Every AgentAnalysis whose recommendation has a ground-truth
        RecommendationOutcome, excluding UNAVAILABLE calls (not
        information-bearing -- same exclusion principle as WATCH
        recommendations in RecommendationRepository.list_unscored)."""
        stmt = (
            select(AgentAnalysis, RecommendationOutcome)
            .join(Recommendation, Recommendation.id == AgentAnalysis.recommendation_id)
            .join(RecommendationOutcome, RecommendationOutcome.recommendation_id == Recommendation.id)
            .where(AgentAnalysis.call != "UNAVAILABLE")
        )
        if role is not None:
            stmt = stmt.where(AgentAnalysis.role == role)
        return [tuple(row) for row in self.db.execute(stmt).all()]
