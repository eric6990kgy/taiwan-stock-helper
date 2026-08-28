from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import Asset


class AssetRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, asset_id: int) -> Asset | None:
        return self.db.get(Asset, asset_id)

    def get_by_ticker(self, ticker: str) -> Asset | None:
        return self.db.execute(select(Asset).where(Asset.ticker == ticker)).scalar_one_or_none()

    def list(self) -> list[Asset]:
        return list(self.db.execute(select(Asset)).scalars().all())

    def create(self, **fields) -> Asset:
        asset = Asset(**fields)
        self.db.add(asset)
        self.db.flush()
        return asset

    def update(self, asset: Asset, **fields) -> Asset:
        for key, value in fields.items():
            if value is not None:
                setattr(asset, key, value)
        self.db.flush()
        return asset

    def delete(self, asset: Asset) -> None:
        self.db.delete(asset)
        self.db.flush()
