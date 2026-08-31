"""Unit tests for ResearchService's Phase 6 additions, using a lightweight
stub MarketDataProvider so these don't need a DB or the FastAPI test client
(complements the API-level tests in tests/api/test_research.py)."""

from datetime import date
from decimal import Decimal

from app.providers.market_data_provider import (
    AssetNotFoundError,
    MarketDataProvider,
    MonthlyRevenueDTO,
    PricePointDTO,
)
from app.services.research_service import ResearchService, _revenue_growth


class StubProvider(MarketDataProvider):
    def __init__(self):
        self.price_points: list[PricePointDTO] = []
        self.monthly_revenue_rows: list[MonthlyRevenueDTO] = []

    def get_historical_prices(self, ticker, start=None, end=None):
        if ticker == "NOPE":
            raise AssetNotFoundError(ticker)
        return [p for p in self.price_points if start is None or p.date >= start]

    def get_monthly_revenue(self, ticker):
        if ticker == "NOPE":
            raise AssetNotFoundError(ticker)
        return self.monthly_revenue_rows

    def get_quote(self, ticker):
        raise NotImplementedError

    def get_company_info(self, ticker):
        raise NotImplementedError

    def get_fundamentals(self, ticker):
        raise NotImplementedError

    def get_dividends(self, ticker, start=None, end=None):
        raise NotImplementedError

    def get_valuation(self, ticker, on_date=None):
        raise NotImplementedError

    def get_institutional_flows(self, ticker, start=None, end=None):
        raise NotImplementedError

    def get_margin_trading(self, ticker, start=None, end=None):
        raise NotImplementedError


def price(d, close) -> PricePointDTO:
    c = Decimal(str(close))
    return PricePointDTO(date=d, open=c, high=c, low=c, close=c, volume=1000, source="FINMIND")


def revenue(year, month, amount) -> MonthlyRevenueDTO:
    return MonthlyRevenueDTO(revenue_year=year, revenue_month=month, revenue=Decimal(amount), announcement_date=None, source="FINMIND")


# ---- get_technical_indicators: no price history -----------------------------------


def test_technical_indicators_no_price_history_returns_null_indicators_not_error():
    provider = StubProvider()
    service = ResearchService(market_data=provider, thesis_service=None)

    result = service.get_technical_indicators("EMPTY")

    assert result.as_of is None
    assert result.source == "CALCULATED"
    for field_name in type(result.indicators).model_fields:
        assert getattr(result.indicators, field_name) is None


def test_technical_indicators_unknown_ticker_raises_not_found():
    from app.services.exceptions import NotFoundError

    provider = StubProvider()
    service = ResearchService(market_data=provider, thesis_service=None)
    try:
        service.get_technical_indicators("NOPE")
        assert False, "expected NotFoundError"
    except NotFoundError:
        pass


def test_technical_indicators_as_of_excludes_future_prices():
    provider = StubProvider()
    provider.price_points = [price(date(2026, 8, d), 100 + d) for d in range(1, 15)]
    service = ResearchService(market_data=provider, thesis_service=None)

    result = service.get_technical_indicators("2330", as_of=date(2026, 8, 10))
    assert result.as_of == date(2026, 8, 10)


# ---- _revenue_growth: YoY / MoM edge cases -----------------------------------------


def test_revenue_growth_yoy_basic():
    rows = [revenue(2025, 7, "100"), revenue(2026, 7, "120")]
    growth = _revenue_growth(rows[1], rows, years_back=1)
    assert growth == (Decimal("120") - Decimal("100")) / Decimal("100")


def test_revenue_growth_yoy_missing_prior_year_returns_none():
    rows = [revenue(2026, 7, "120")]  # no 2025-07 row at all
    assert _revenue_growth(rows[0], rows, years_back=1) is None


def test_revenue_growth_mom_missing_previous_month_returns_none():
    rows = [revenue(2026, 7, "120")]  # no 2026-06 row
    assert _revenue_growth(rows[0], rows, years_back=0) is None


def test_revenue_growth_mom_handles_january_december_year_rollover():
    rows = [revenue(2025, 12, "100"), revenue(2026, 1, "110")]
    growth = _revenue_growth(rows[1], rows, years_back=0)
    assert growth == (Decimal("110") - Decimal("100")) / Decimal("100")


def test_revenue_growth_zero_denominator_returns_none_not_fake_zero():
    rows = [revenue(2025, 7, "0"), revenue(2026, 7, "120")]
    assert _revenue_growth(rows[1], rows, years_back=1) is None


def test_revenue_growth_newly_listed_company_first_row_has_no_comparisons():
    rows = [revenue(2026, 7, "120")]  # the only row that exists
    assert _revenue_growth(rows[0], rows, years_back=1) is None
    assert _revenue_growth(rows[0], rows, years_back=0) is None