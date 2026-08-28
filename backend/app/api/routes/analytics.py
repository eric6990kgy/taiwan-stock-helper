from fastapi import APIRouter, Depends

from app.api.deps import get_analytics_service
from app.schemas.analytics import AllocationRead, PerformanceRead, RiskRead
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/allocation", response_model=AllocationRead)
def get_allocation(service: AnalyticsService = Depends(get_analytics_service)):
    return service.get_allocation()


@router.get("/performance", response_model=PerformanceRead)
def get_performance(service: AnalyticsService = Depends(get_analytics_service)):
    return service.get_performance()


@router.get("/risk", response_model=RiskRead)
def get_risk(service: AnalyticsService = Depends(get_analytics_service)):
    return service.get_risk()
