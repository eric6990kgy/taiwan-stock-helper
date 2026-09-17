from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.repositories.asset_repository import AssetRepository
from app.repositories.transaction_repository import TransactionRepository
from app.services.exceptions import DuplicateError, NotFoundError


class AssetService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AssetRepository(db)
        self.transactions_repo = TransactionRepository(db)

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
        # Asset.transactions carries the same ORM-level `cascade="all,
        # delete-orphan"` as Account.transactions (see AccountService.delete
        # for the incident this pattern caused there) -- deleting an asset
        # with real transaction history would otherwise silently destroy
        # that history too. Financial transaction history must never be
        # destroyed as a side effect of an unrelated action.
        if self.transactions_repo.list(asset_id=asset_id, limit=1):
            raise ValueError(
                f"Cannot delete asset {asset_id!r}: it still has transactions. "
                "Delete its transactions first if you really want to remove this asset."
            )
        self.repo.delete(asset)
        self.db.commit()
