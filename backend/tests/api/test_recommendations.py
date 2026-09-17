from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.api.deps import get_finmind_provider
from app.main import app
from app.providers.market_data_provider import AssetNotFoundError, MarketDataProvider, PricePointDTO


class StubProvider(MarketDataProvider):
    """Minimal stand-in for FinMindProvider -- same pattern as
    test_market_data_route.py's StubProvider, scoped to just what
    triggering a Phase 8 daily scan through /api/market-data/update needs."""

    def __init__(self):
        self.prices: dict[str, object] = {}

    def get_historical_prices(self, ticker, start=None, end=None):
        return self.prices.get(ticker, [])

    def get_valuation(self, ticker, on_date=None):
        raise AssetNotFoundError(ticker)

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


def price_point(d: date, close: str) -> PricePointDTO:
    c = Decimal(close)
    return PricePointDTO(date=d, open=c, high=c, low=c, close=c, volume=1000, source="FINMIND")


def test_recommendations_endpoint_is_empty_before_any_scan_has_run(client):
    resp = client.get("/api/recommendations")
    assert resp.status_code == 200
    assert resp.json() == []


def add_fresh_watchlist_ticker(client, ticker="9999") -> None:
    """A brand-new ticker with no seeded fundamentals/price history --
    unlike the demo seed's own watchlist entry (3491), this keeps
    COMPOSITE_SCORE UNAVAILABLE throughout (no valuation/fundamentals ever
    lands for it via StubProvider), so overall_status is driven purely by
    the injected price series, making the transition predictable."""
    create_resp = client.post(
        "/api/assets", json={"ticker": ticker, "name": "Test Co", "asset_type": "STOCK", "market": "TWSE", "currency": "TWD"}
    )
    assert create_resp.status_code == 201
    asset_id = create_resp.json()["id"]
    watchlist_resp = client.post("/api/watchlist", json={"asset_id": asset_id, "status": "WATCHING"})
    assert watchlist_resp.status_code == 201


def test_recommendations_endpoint_reflects_a_scan_triggered_by_market_data_update(client, stub_provider):
    """/api/market-data/update runs the daily scan as its last step (Phase
    8). The first scan only establishes a baseline (per the "only on
    change" rule), so the second update -- with a clear uptrend -- is the
    one expected to produce a CONSIDER_INCREASE recommendation."""
    add_fresh_watchlist_ticker(client, "9999")
    start = date.today() - timedelta(days=64)

    flat = [price_point(start + timedelta(days=i), "100") for i in range(65)]
    stub_provider.prices["9999"] = flat
    first = client.post("/api/market-data/update", params={"tickers": ["9999"]})
    assert first.status_code == 200

    rising = [price_point(start + timedelta(days=i), str(100 + i)) for i in range(65)]
    stub_provider.prices["9999"] = rising
    second = client.post("/api/market-data/update", params={"tickers": ["9999"]})
    assert second.status_code == 200

    resp = client.get("/api/recommendations")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["ticker"] == "9999"
    assert body[0]["action"] == "CONSIDER_INCREASE"
    assert body[0]["new_status"] == "BULLISH"
    # Phase 12: always present, empty without GEMINI_API_KEY configured
    # (the test environment never sets one) -- never absent from the payload.
    assert body[0]["agent_analyses"] == []


def test_recommendations_endpoint_since_filter(client, stub_provider):
    add_fresh_watchlist_ticker(client, "9999")
    flat = [price_point(date(2026, 7, 1) + timedelta(days=i), "100") for i in range(65)]
    stub_provider.prices["9999"] = flat
    client.post("/api/market-data/update", params={"tickers": ["9999"]})

    future_cutoff = (date.today() + timedelta(days=1)).isoformat() + "T00:00:00"
    resp = client.get(f"/api/recommendations?since={future_cutoff}")
    assert resp.status_code == 200
    assert resp.json() == []
