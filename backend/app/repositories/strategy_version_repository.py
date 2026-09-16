from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.strategy_version import StrategyVersion


class StrategyVersionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, version_id: int) -> StrategyVersion | None:
        return self.db.get(StrategyVersion, version_id)

    def get_active(self) -> StrategyVersion | None:
        stmt = select(StrategyVersion).where(StrategyVersion.status == "ACTIVE")
        return self.db.execute(stmt).scalar_one_or_none()

    def latest_version_number(self) -> int:
        stmt = select(StrategyVersion).order_by(StrategyVersion.version_number.desc())
        latest = self.db.execute(stmt).scalars().first()
        return latest.version_number if latest is not None else 0

    def list(self) -> list[StrategyVersion]:
        stmt = select(StrategyVersion).order_by(StrategyVersion.version_number.desc())
        return list(self.db.execute(stmt).scalars().all())

    def create(self, **fields) -> StrategyVersion:
        version = StrategyVersion(**fields)
        self.db.add(version)
        self.db.flush()
        return version

    def update(self, version: StrategyVersion, **fields) -> StrategyVersion:
        for key, value in fields.items():
            setattr(version, key, value)
        self.db.flush()
        return version
