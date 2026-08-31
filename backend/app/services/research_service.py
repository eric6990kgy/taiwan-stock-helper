from datetime import date, timedelta
from decimal import Decimal

from app.analytics import technical
from app.providers.market_data_provider import AssetNotFoundError, MarketDataProvider, MonthlyRevenueDTO
from app.schemas.research import (
    FundamentalsRead,
    InstitutionalFlowRead,
    MarginTradingRead,
    MonthlyRevenueRead,
    PricePointRead,
    QuoteRead,
    ResearchPageRead,
    TechnicalIndicatorsRead,
    TechnicalIndicatorValues,
)
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
        # Explicit field mapping, not **vars(r) -- PricePointDTO gained
        # adjusted_close/trading_value in Phase 5B that PricePointRead
        # doesn't expose yet, and **vars(r) would break on the extra keys.
        return [
            PricePointRead(date=r.date, open=r.open, high=r.high, low=r.low, close=r.close, volume=r.volume, source=r.source)
            for r in rows
        ]

    def get_institutional_flows(self, ticker: str, range_key: str | None = None) -> list[InstitutionalFlowRead]:
        start = self._range_start(ticker, range_key) if range_key else None
        try:
            rows = self.market_data.get_institutional_flows(ticker, start=start)
        except AssetNotFoundError as exc:
            raise NotFoundError(str(exc)) from exc
        return [InstitutionalFlowRead(**vars(r)) for r in rows]

    def get_margin_trading(self, ticker: str, range_key: str | None = None) -> list[MarginTradingRead]:
        start = self._range_start(ticker, range_key) if range_key else None
        try:
            rows = self.market_data.get_margin_trading(ticker, start=start)
        except AssetNotFoundError as exc:
            raise NotFoundError(str(exc)) from exc
        return [MarginTradingRead(**vars(r)) for r in rows]

    def get_monthly_revenue(self, ticker: str) -> list[MonthlyRevenueRead]:
        try:
            rows = self.market_data.get_monthly_revenue(ticker)
        except AssetNotFoundError as exc:
            raise NotFoundError(str(exc)) from exc

        return [
            MonthlyRevenueRead(
                revenue_year=r.revenue_year,
                revenue_month=r.revenue_month,
                revenue=r.revenue,
                yoy_growth=_revenue_growth(r, rows, years_back=1),
                mom_growth=_revenue_growth(r, rows, years_back=0),
                announcement_date=r.announcement_date,
                source=r.source,
            )
            for r in rows
        ]

    def get_technical_indicators(self, ticker: str, as_of: date | None = None) -> TechnicalIndicatorsRead:
        try:
            points = self.market_data.get_historical_prices(ticker)
        except AssetNotFoundError as exc:
            raise NotFoundError(str(exc)) from exc

        points = sorted(points, key=lambda p: p.date)
        if as_of is not None:
            points = [p for p in points if p.date <= as_of]

        if not points:
            empty = TechnicalIndicatorValues(**technical.latest_snapshot([], [], []))
            return TechnicalIndicatorsRead(ticker=ticker, as_of=None, indicators=empty, source="CALCULATED")

        closes = [p.close for p in points]
        highs = [p.high if p.high is not None else p.close for p in points]
        lows = [p.low if p.low is not None else p.close for p in points]

        snapshot = technical.latest_snapshot(closes, highs, lows)
        values = TechnicalIndicatorValues(**snapshot)
        return TechnicalIndicatorsRead(ticker=ticker, as_of=points[-1].date, indicators=values, source="CALCULATED")

    def _range_start(self, ticker: str, range_key: str) -> date:
        quote = self.market_data.get_quote(ticker)
        days = RANGE_DAYS.get(range_key.upper())
        if days is None:
            raise ValueError(f"Unsupported range: {range_key!r}. Use one of {list(RANGE_DAYS)}.")
        return quote.as_of - timedelta(days=days)


def _revenue_growth(current: MonthlyRevenueDTO, all_rows: list[MonthlyRevenueDTO], years_back: int) -> Decimal | None:
    """years_back=1 -> YoY (same month, prior year). years_back=0 -> MoM
    (previous calendar month, handling the December/January year rollover).
    None whenever the comparison period is missing or would divide by zero
    -- never a fabricated 0% (e.g. a newly listed company with no prior-year
    data, or the very first row in the series)."""
    if years_back == 1:
        target_year, target_month = current.revenue_year - 1, current.revenue_month
    else:
        if current.revenue_month == 1:
            target_year, target_month = current.revenue_year - 1, 12
        else:
            target_year, target_month = current.revenue_year, current.revenue_month - 1

    comparison = next(
        (r for r in all_rows if r.revenue_year == target_year and r.revenue_month == target_month), None
    )
    if comparison is None or comparison.revenue == 0:
        return None
    return (current.revenue - comparison.revenue) / comparison.revenue
