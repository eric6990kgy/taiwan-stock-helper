from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_market_data_service
from app.schemas.market_data import MarketDataUpdateResult
from app.services.market_data_service import MarketDataIngestionService

router = APIRouter(prefix="/api/market-data", tags=["market-data"])


@router.post("/update", response_model=MarketDataUpdateResult)
def update_market_data(
    tickers: Annotated[list[str] | None, Query()] = None,
    service: MarketDataIngestionService = Depends(get_market_data_service),
):
    """Manual trigger only (Phase 5B) -- the daily-scheduled half of the
    hybrid ingestion architecture is deliberately not built yet. Omit
    `tickers` to update every STOCK/ETF asset in the database. Repeat the
    query param to filter to more than one (?tickers=2330&tickers=2317) --
    a bare `list[str] | None` parameter is silently ignored by FastAPI's
    query-param inference and must be explicitly annotated with Query()."""
    return service.update_all(tickers=tickers)
