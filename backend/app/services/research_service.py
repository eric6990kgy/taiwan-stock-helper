from datetime import date, timedelta

from app.providers.market_data_provider import AssetNotFoundError, MarketDataProvider
from app.schemas.research import FundamentalsRead, PricePointRead, QuoteRead, ResearchPageRead
from app.schemas.thesis import ThesisRead
from app.services.exceptions import NotFoundError
from app.services.thesis_service import ThesisService

RANGE_DAYS = {
    "1M": 31,
    "3M": 92,
    "6M": 183,
    "1Y": 366,
    "3Y": 366 * 3,
    "5Y": 366 * 5,
}


class ResearchService:
    def __init__(self, market_data: MarketDataProvider, thesis_service: ThesisService):
        self.market_data = market_data
        self.thesis_service = thesis_service

    def get_research_page(self, ticker: str) -> ResearchPageRead:
        try:
            info = self.market_data.get_company_info(ticker)
            quote = self.market_data.get_quote(ticker)
        except AssetNotFoundError as exc:
            raise NotFoundError(str(exc)) from exc

        fundamentals = self.market_data.get_fundamentals(ticker)
        ttm = next((f for f in fundamentals if f.period == "TTM"), None)

        try:
            thesis: ThesisRead | None = self.thesis_service.get_by_ticker(ticker)
        except NotFoundError:
            thesis = None

        return ResearchPageRead(
            ticker=info.ticker,
            name=info.name,
            asset_type=info.asset_type,
            market=info.market,
            sector=info.sector,
            industry=info.industry,
            is_demo_data=info.is_demo_data,
            quote=QuoteRead(
                ticker=quote.ticker,
                price=quote.price,
                as_of=quote.as_of,
                high_52w=quote.high_52w,
                low_52w=quote.low_52w,
            ),
            latest_fundamentals=FundamentalsRead(**vars(ttm)) if ttm else None,
            thesis=thesis,
        )

    def get_fundamentals(self, ticker: str) -> list[FundamentalsRead]:
        try:
            rows = self.market_data.get_fundamentals(ticker)
        except AssetNotFoundError as exc:
            raise NotFoundError(str(exc)) from exc
        return [FundamentalsRead(**vars(r)) for r in rows]

    def get_prices(self, ticker: str, range_key: str | None = None) -> list[PricePointRead]:
        try:
            quote = self.market_data.get_quote(ticker)
        except AssetNotFoundError as exc:
            raise NotFoundError(str(exc)) from exc

        start = None
        if range_key:
            days = RANGE_DAYS.get(range_key.upper())
            if days is None:
                raise ValueError(f"Unsupported range: {range_key!r}. Use one of {list(RANGE_DAYS)}.")
            start = quote.as_of - timedelta(days=days)

        rows = self.market_data.get_historical_prices(ticker, start=start)
        return [PricePointRead(**vars(r)) for r in rows]
