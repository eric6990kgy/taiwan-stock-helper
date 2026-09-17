from fastapi import APIRouter, Depends

from app.api.deps import get_recommendation_outcome_service
from app.schemas.review import RecommendationOutcomeRead, ReviewSummaryRead
from app.services.recommendation_outcome_service import RecommendationOutcomeService

router = APIRouter(prefix="/api/review", tags=["review"])


@router.get("/summary", response_model=ReviewSummaryRead)
def get_review_summary(action: str | None = None, service: RecommendationOutcomeService = Depends(get_recommendation_outcome_service)):
    return service.get_review_summary_read(action=action)


@router.get("/outcomes", response_model=list[RecommendationOutcomeRead])
def list_review_outcomes(action: str | None = None, service: RecommendationOutcomeService = Depends(get_recommendation_outcome_service)):
    return service.list_outcomes_read(action=action)
