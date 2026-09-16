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
        # INDEX assets (TAIEX) are internal bookkeeping for Phase 7 regime
        # detection -- never a personal holding, so they must never appear
        # in a ticker/asset picker (Research, Watchlist, Transactions all
        # share this one endpoint). MarketDataIngestionService/ScreenerService
        # call AssetRepository.list() directly and filter to STOCK/ETF
        # themselves, so this exclusion only affects picker-facing reads.
        return [a for a in self.repo.list() if a.asset_type != "INDEX"]

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
