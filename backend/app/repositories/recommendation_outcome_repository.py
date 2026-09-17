from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.recommendation_outcome import RecommendationOutcome


class RecommendationOutcomeRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_recommendation(self, recommendation_id: int) -> RecommendationOutcome | None:
        stmt = select(RecommendationOutcome).where(RecommendationOutcome.recommendation_id == recommendation_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list(self, action: str | None = None) -> list[RecommendationOutcome]:
        """Newest-scored first. `action` filters by the parent
        Recommendation's action (CONSIDER_INCREASE vs CONSIDER_DECREASE
        imply opposite directions, so callers usually want them separate)."""
        from app.models.recommendation import Recommendation

        stmt = select(RecommendationOutcome).join(Recommendation)
        if action is not None:
            stmt = stmt.where(Recommendation.action == action)
        stmt = stmt.order_by(RecommendationOutcome.computed_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def create(self, **fields) -> RecommendationOutcome:
        row = RecommendationOutcome(**fields)
        self.db.add(row)
        self.db.flush()
        return row
