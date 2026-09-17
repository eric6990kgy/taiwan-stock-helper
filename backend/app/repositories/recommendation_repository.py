from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.recommendation import Recommendation
from app.models.recommendation_outcome import RecommendationOutcome


class RecommendationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **fields) -> Recommendation:
        row = Recommendation(**fields)
        self.db.add(row)
        self.db.flush()
        return row

    def list_unscored(self) -> list[Recommendation]:
        """Every WATCH-excluded recommendation that doesn't have a
        RecommendationOutcome row yet (Phase 10) -- WATCH is never scored
        since it makes no directional claim (see ACTION_BY_STATUS).
        Defined before list() below: once a method literally named `list`
        is bound in this class's namespace, it shadows the builtin for
        every `list[...]` annotation that follows it in the class body
        (same gotcha documented on TransactionRepository.list_all)."""
        stmt = (
            select(Recommendation)
            .outerjoin(RecommendationOutcome, RecommendationOutcome.recommendation_id == Recommendation.id)
            .where(Recommendation.action != "WATCH", RecommendationOutcome.id.is_(None))
            .order_by(Recommendation.created_at)
        )
        return list(self.db.execute(stmt).scalars().all())

    def list(self, since: datetime | None = None) -> list[Recommendation]:
        """Newest first. `since` filters to recommendations created on or
        after that timestamp -- e.g. the start of today's scan, for a
        "today's recommendations" view."""
        stmt = select(Recommendation)
        if since is not None:
            stmt = stmt.where(Recommendation.created_at >= since)
        stmt = stmt.order_by(Recommendation.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())
