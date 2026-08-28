from fastapi import APIRouter, Depends

from app.api.deps import get_portfolio_service
from app.schemas.portfolio import HoldingRead, PortfolioSummaryRead
from app.services.portfolio_service import PortfolioService

router = APIRouter(prefix="/api", tags=["portfolio"])


@router.get("/portfolio", response_model=PortfolioSummaryRead)
def get_portfolio_summary(service: PortfolioService = Depends(get_portfolio_service)):
    return service.get_summary()


@router.get("/holdings", response_model=list[HoldingRead])
def get_holdings(account_id: int | None = None, service: PortfolioService = Depends(get_portfolio_service)):
    return service.get_holdings(account_id=account_id)
