from datetime import datetime

from fastapi import APIRouter, Depends

from app.api.deps import get_recommendation_service
from app.schemas.recommendation import RecommendationRead
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("", response_model=list[RecommendationRead])
def list_recommendations(since: datetime | None = None, service: RecommendationService = Depends(get_recommendation_service)):
    """Newest first. Only tickers whose signal status actually changed on
    some past scan ever appear here -- an unchanged ticker never gets a
    row (個股訊號引擎規格書 Phase B Sec.05 P0)."""
    return service.list_recommendations(since=since)
