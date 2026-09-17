from fastapi import APIRouter, Depends

from app.api.deps import get_agent_performance_service
from app.schemas.review import ReviewSummaryRead
from app.services.agent_performance_service import AgentPerformanceService

router = APIRouter(prefix="/api/agent-performance", tags=["agent-performance"])


@router.get("/summary", response_model=ReviewSummaryRead)
def get_agent_performance_summary(
    role: str | None = None, service: AgentPerformanceService = Depends(get_agent_performance_service)
):
    return service.get_summary_read(role=role)
