from app.models.dividend import Dividend
from app.repositories.asset_date_repository import AssetDateRepository


class DividendRepository(AssetDateRepository[Dividend]):
    model = Dividend
    date_column = "ex_dividend_date"
