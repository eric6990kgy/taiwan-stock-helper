from decimal import Decimal

from fastapi import APIRouter, Depends

from app.api.deps import get_screener_service
from app.schemas.screener import ScreenerResult
from app.services.screener_service import ScreenerService

router = APIRouter(prefix="/api/screener", tags=["screener"])


@router.get("", response_model=list[ScreenerResult])
def screen(
    revenue_growth_gt: Decimal | None = None,
    roe_gt: Decimal | None = None,
    pe_lt: Decimal | None = None,
    market_cap_gt: Decimal | None = None,
    dividend_yield_gt: Decimal | None = None,
    foreign_net_buy_gt: int | None = None,
    rsi_lt: Decimal | None = None,
    rsi_gt: Decimal | None = None,
    above_sma_20: bool | None = None,
    service: ScreenerService = Depends(get_screener_service),
):
    return service.screen(
        revenue_growth_gt=revenue_growth_gt,
        roe_gt=roe_gt,
        pe_lt=pe_lt,
        market_cap_gt=market_cap_gt,
        dividend_yield_gt=dividend_yield_gt,
        foreign_net_buy_gt=foreign_net_buy_gt,
        rsi_lt=rsi_lt,
        rsi_gt=rsi_gt,
        above_sma_20=above_sma_20,
    )
