from fastapi import APIRouter, Depends

from app.api.deps import get_strategy_service
from app.schemas.strategy import PendingStrategyChangeRead, ProposeStrategyChangeRequest, StrategyVersionRead
from app.services.strategy_service import StrategyService, pending_to_read, version_to_read

router = APIRouter(prefix="/api/strategy", tags=["strategy"])


@router.get("/versions", response_model=list[StrategyVersionRead])
def list_versions(service: StrategyService = Depends(get_strategy_service)):
    return service.list_versions()


@router.post("/versions", response_model=StrategyVersionRead | PendingStrategyChangeRead)
def propose_version(payload: ProposeStrategyChangeRequest, service: StrategyService = Depends(get_strategy_service)):
    """Same parameter keys as the active version -> applied immediately
    (returns the new StrategyVersion). A different key set -> queued for
    confirmation (returns the PendingStrategyChange) -- never silently
    promoted (個股訊號引擎規格書 Phase B 07)."""
    result = service.propose_change(payload.proposed_rules, payload.reason)
    if result.__class__.__name__ == "StrategyVersion":
        return version_to_read(result)
    return pending_to_read(result)


@router.get("/pending", response_model=list[PendingStrategyChangeRead])
def list_pending(status: str | None = None, service: StrategyService = Depends(get_strategy_service)):
    return service.list_pending(status=status)


@router.post("/pending/{change_id}/confirm", response_model=StrategyVersionRead)
def confirm_pending(change_id: int, service: StrategyService = Depends(get_strategy_service)):
    return version_to_read(service.confirm_pending(change_id))


@router.post("/pending/{change_id}/reject", response_model=PendingStrategyChangeRead)
def reject_pending(change_id: int, service: StrategyService = Depends(get_strategy_service)):
    return pending_to_read(service.reject_pending(change_id))
