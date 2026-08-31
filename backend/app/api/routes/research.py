from datetime import date

from fastapi import APIRouter, Depends

from app.api.deps import get_research_service
from app.schemas.research import (
    FundamentalsRead,
    InstitutionalFlowRead,
    MarginTradingRead,
    MonthlyRevenueRead,
    PricePointRead,
    ResearchPageRead,
    TechnicalIndicatorsRead,
)
from app.services.research_service import ResearchService

router = APIRouter(prefix="/api", tags=["research"])


@router.get("/research/{ticker}", response_model=ResearchPageRead)
def get_research_page(ticker: str, service: ResearchService = Depends(get_research_service)):
    return service.get_research_page(ticker)


@router.get("/fundamentals/{ticker}", response_model=list[FundamentalsRead])
def get_fundamentals(ticker: str, service: ResearchService = Depends(get_research_service)):
    return service.get_fundamentals(ticker)


@router.get("/prices/{ticker}", response_model=list[PricePointRead])
def get_prices(ticker: str, range: str | None = None, service: ResearchService = Depends(get_research_service)):
    return service.get_prices(ticker, range_key=range)


@router.get("/research/{ticker}/institutional", response_model=list[InstitutionalFlowRead])
def get_institutional_flows(ticker: str, range: str | None = None, service: ResearchService = Depends(get_research_service)):
    return service.get_institutional_flows(ticker, range_key=range)


@router.get("/research/{ticker}/margin", response_model=list[MarginTradingRead])
def get_margin_trading(ticker: str, range: str | None = None, service: ResearchService = Depends(get_research_service)):
    return service.get_margin_trading(ticker, range_key=range)


@router.get("/research/{ticker}/revenue", response_model=list[MonthlyRevenueRead])
def get_monthly_revenue(ticker: str, service: ResearchService = Depends(get_research_service)):
    return service.get_monthly_revenue(ticker)


@router.get("/research/{ticker}/technical", response_model=TechnicalIndicatorsRead)
def get_technical_indicators(ticker: str, as_of: date | None = None, service: ResearchService = Depends(get_research_service)):
    return service.get_technical_indicators(ticker, as_of=as_of)
