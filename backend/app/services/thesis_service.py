from sqlalchemy.orm import Session

from app.repositories.asset_repository import AssetRepository
from app.repositories.thesis_repository import ThesisRepository
from app.schemas.thesis import ThesisRead
from app.services.exceptions import NotFoundError


class ThesisService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ThesisRepository(db)
        self.assets = AssetRepository(db)

    def _to_read(self, thesis) -> ThesisRead:
        asset = self.assets.get(thesis.asset_id)
        return ThesisRead(
            id=thesis.id,
            asset_id=thesis.asset_id,
            ticker=asset.ticker,
            thesis=thesis.thesis,
            catalysts=thesis.catalysts,
            risks=thesis.risks,
            key_metrics=thesis.key_metrics,
            status=thesis.status,
            last_reviewed=thesis.last_reviewed,
            updated_at=thesis.updated_at,
        )

    def get_by_ticker(self, ticker: str) -> ThesisRead:
        asset = self.assets.get_by_ticker(ticker)
        if asset is None:
            raise NotFoundError(f"Asset with ticker {ticker!r} not found.")
        thesis = self.repo.get_by_asset(asset.id)
        if thesis is None:
            raise NotFoundError(f"No investment thesis exists yet for {ticker!r}.")
        return self._to_read(thesis)

    def upsert_by_ticker(self, ticker: str, **fields) -> ThesisRead:
        """PUT /api/thesis/{ticker} — creates on first write, updates after,
        since PRD Sec.15 treats a stock's thesis as a single evolving record."""
        asset = self.assets.get_by_ticker(ticker)
        if asset is None:
            raise NotFoundError(f"Asset with ticker {ticker!r} not found.")

        existing = self.repo.get_by_asset(asset.id)
        if existing is None:
            thesis = self.repo.create(asset_id=asset.id, **fields)
        else:
            thesis = self.repo.update(existing, **fields)
        self.db.commit()
        return self._to_read(thesis)
