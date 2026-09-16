from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.signal_snapshot import SignalSnapshot


class SignalSnapshotRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_asset(self, asset_id: int) -> SignalSnapshot | None:
        stmt = select(SignalSnapshot).where(SignalSnapshot.asset_id == asset_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def upsert(self, asset_id: int, overall_status: str) -> SignalSnapshot:
        existing = self.get_by_asset(asset_id)
        if existing is None:
            snapshot = SignalSnapshot(asset_id=asset_id, overall_status=overall_status)
            self.db.add(snapshot)
            self.db.flush()
            return snapshot
        existing.overall_status = overall_status
        self.db.flush()
        return existing
