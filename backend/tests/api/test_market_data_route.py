"""Settings' "Update Market Data" flow, exercised through the real FastAPI
route with app.api.deps.get_finmind_provider overridden to a stub -- no
real network calls. A batch result (partial success, rate limit) is
reported in the 200 response body's `status`/`failed` fields, never as an
HTTP error code for the whole request: one bad ticker in a 7-ticker batch
isn't "the request failed."
"""

from datetime import date
from decimal import Decimal

import pytest

from app.api.deps import get_finmind_provider
from app.main import app
from app.providers.market_data_provider import (
    AssetNotFoundError,
    MarketDataProvider,
    PricePointDTO,
    ProviderError,
    RateLimitError,
)


class StubProvider(MarketDataProvider):
    def __init__(self):
        self.prices: dict[str, object] = {}

    def get_historical_prices(self, ticker, start=None, end=None):
        result = self.prices.get(ticker, [])
        if isinstance(result, Exception):
            raise result
        return result

    def get_valuation(self, ticker, on_date=None):
        raise AssetNotFoundError(ticker)  # not exercised by these tests

    def get_fundamentals(self, ticker):
        return []

    def get_dividends(self, ticker, start=None, end=None):
        return []

    def get_institutional_flows(self, ticker, start=None, end=None):
        return []

    def get_margin_trading(self, ticker, start=None, end=None):
        return []

    def get_monthly_revenue(self, ticker):
        return []

    def get_quote(self, ticker):
        raise NotImplementedError

    def get_company_info(self, ticker):
        raise NotImplementedError


@pytest.fixture()
def stub_provider(client):
    provider = StubProvider()

    def override():
        yield provider

    app.dependency_overrides[get_finmind_provider] = override
    yield provider
    app.dependency_overrides.pop(get_finmind_provider, None)


def price_point(d: date, close="100") -> PricePointDTO:
    c = Decimal(close)
    return PricePointDTO(date=d, open=c, high=c, low=c, close=c, volume=1000, source="FINMIND")


def test_update_market_data_returns_result_shape(client, stub_provider):
    stub_provider.prices["3653"] = [price_point(date(2026, 8, 28), close="650")]

    resp = client.post("/api/market-data/update?tickers=3653")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    assert body["source"] == "FINMIND"
    assert "3653" in body["succeeded"]
    assert body["failed"] == []
    assert body["latest_data_date"] == "2026-08-28"


def test_update_market_data_reports_provider_failure_in_body_not_as_http_error(client, stub_provider):
    stub_provider.prices["3653"] = ProviderError("FinMind is unreachable")

    resp = client.post("/api/market-data/update?tickers=3653")

    assert resp.status_code == 200  # the request itself succeeded -- the batch reports its own failures
    body = resp.json()
    assert body["succeeded"] == []
    assert len(body["failed"]) == 1
    assert body["failed"][0]["ticker"] == "3653"
    assert "unreachable" in body["failed"][0]["reason"]


def test_update_market_data_rate_limit_reported_as_status_field(client, stub_provider):
    stub_provider.prices["3653"] = RateLimitError("quota exceeded")

    resp = client.post("/api/market-data/update?tickers=3653")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "rate_limited"
    assert "quota exceeded" in body["failed"][0]["reason"]


def test_update_market_data_filters_by_requested_tickers(client, stub_provider):
    stub_provider.prices["3653"] = [price_point(date(2026, 8, 28))]
    stub_provider.prices["3533"] = [price_point(date(2026, 8, 28))]

    resp = client.post("/api/market-data/update?tickers=3653")

    assert resp.status_code == 200
    body = resp.json()
    assert body["assets_processed"] == 1
    assert body["succeeded"] == ["3653"]


def test_update_market_data_with_no_tickers_processes_all_eligible_seeded_assets(client, stub_provider):
    """Seed data has 7 STOCK tickers + 1 FUND + 1 CASH -- only the 7 stocks
    are eligible for market-data ingestion (architecture decision A4)."""
    resp = client.post("/api/market-data/update")

    assert resp.status_code == 200
    assert resp.json()["assets_processed"] == 7
