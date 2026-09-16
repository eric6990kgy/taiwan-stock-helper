from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.recommendation import Recommendation


class RecommendationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **fields) -> Recommendation:
        row = Recommendation(**fields)
        self.db.add(row)
        self.db.flush()
        return row

    def list(self, since: datetime | None = None) -> list[Recommendation]:
        """Newest first. `since` filters to recommendations created on or
        after that timestamp -- e.g. the start of today's scan, for a
        "today's recommendations" view."""
        stmt = select(Recommendation)
        if since is not None:
            stmt = stmt.where(Recommendation.created_at >= since)
        stmt = stmt.order_by(Recommendation.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())
