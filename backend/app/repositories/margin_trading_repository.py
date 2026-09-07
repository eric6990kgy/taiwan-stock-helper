from app.models.margin_trading import MarginTrading
from app.repositories.asset_date_repository import AssetDateRepository


class MarginTradingRepository(AssetDateRepository[MarginTrading]):
    model = MarginTrading
