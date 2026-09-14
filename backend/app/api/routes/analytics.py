from fastapi import APIRouter, Depends

from app.api.deps import get_analytics_service
from app.schemas.analytics import AllocationRead, BenchmarkComparisonRead, DrawdownRead, PerformanceRead, RiskRead
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


@router.get("/drawdown", response_model=DrawdownRead | None)
def get_drawdown(lookback_days: int = 365, service: AnalyticsService = Depends(get_analytics_service)):
    """Portfolio drawdown-from-peak vs. the confirmed -15%/-25% circuit
    breaker (個股訊號引擎規格書 Phase A). null when there's no transaction
    history yet to evaluate."""
    return service.get_drawdown(lookback_days=lookback_days)


@router.get("/benchmark", response_model=BenchmarkComparisonRead)
def get_benchmark(lookback_days: int = 365, service: AnalyticsService = Depends(get_analytics_service)):
    """Portfolio return vs. the configured passive benchmark (default 0050)
    and the resulting alpha (個股訊號引擎規格書 Goal — excess return over
    what's already held passively, not a raw win rate)."""
    return service.get_benchmark_comparison(lookback_days=lookback_days)
