from sqlalchemy import select

from app.models.price_history import PriceHistory
from app.repositories.asset_date_repository import AssetDateRepository


class PriceRepository(AssetDateRepository[PriceHistory]):
    model = PriceHistory

    def latest(self, asset_id: int) -> PriceHistory | None:
        stmt = select(PriceHistory).where(PriceHistory.asset_id == asset_id).order_by(PriceHistory.date.desc()).limit(1)
        return self.db.execute(stmt).scalar_one_or_none()
