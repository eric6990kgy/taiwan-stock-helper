from app.models.score import Score
from app.repositories.asset_date_repository import AssetDateRepository


class ScoreRepository(AssetDateRepository[Score]):
    model = Score
