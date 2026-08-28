from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.thesis import InvestmentThesis


class ThesisRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_asset(self, asset_id: int) -> InvestmentThesis | None:
        return self.db.execute(
            select(InvestmentThesis).where(InvestmentThesis.asset_id == asset_id)
        ).scalar_one_or_none()

    def create(self, **fields) -> InvestmentThesis:
        thesis = InvestmentThesis(**fields)
        self.db.add(thesis)
        self.db.flush()
        return thesis

    def update(self, entry: InvestmentThesis, **fields) -> InvestmentThesis:
        # Parameter name deliberately not "thesis" -- ThesisUpsert has a
        # field literally named `thesis`, which would collide via **fields.
        for key, value in fields.items():
            if value is not None:
                setattr(entry, key, value)
        self.db.flush()
        return entry
