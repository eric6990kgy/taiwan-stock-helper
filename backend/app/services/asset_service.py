from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.repositories.asset_repository import AssetRepository
from app.services.exceptions import DuplicateError, NotFoundError


class AssetService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AssetRepository(db)

    def get(self, asset_id: int) -> Asset:
        asset = self.repo.get(asset_id)
        if asset is None:
            raise NotFoundError(f"Asset {asset_id} not found.")
        return asset

    def get_by_ticker(self, ticker: str) -> Asset:
        asset = self.repo.get_by_ticker(ticker)
        if asset is None:
            raise NotFoundError(f"Asset with ticker {ticker!r} not found.")
        return asset

    def list(self) -> list[Asset]:
        return self.repo.list()

    def create(self, **fields) -> Asset:
        try:
            asset = self.repo.create(**fields)
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise DuplicateError(f"Asset with ticker {fields.get('ticker')!r} already exists.") from exc
        return asset

    def update(self, asset_id: int, **fields) -> Asset:
        asset = self.get(asset_id)
        self.repo.update(asset, **fields)
        self.db.commit()
        return asset

    def delete(self, asset_id: int) -> None:
        asset = self.get(asset_id)
        self.repo.delete(asset)
        self.db.commit()
