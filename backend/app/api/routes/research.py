from fastapi import APIRouter, Depends

from app.api.deps import get_research_service
from app.schemas.research import FundamentalsRead, PricePointRead, ResearchPageRead
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
