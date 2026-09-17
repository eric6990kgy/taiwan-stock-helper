"""Review (複盤) endpoints -- aggregate hit-rate summary and per-outcome
drill-down (Phase 10). Exercised end-to-end through /api/market-data/update
(same StubProvider pattern as test_recommendations.py), since that's the
only way a Recommendation -- and, once enough future price history exists,
a scored RecommendationOutcome -- actually gets created.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.api.deps import get_finmind_provider
from app.main import app
from app.providers.market_data_provider import AssetNotFoundError, MarketDataProvider, PricePointDTO


class StubProvider(MarketDataProvider):
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


def add_fresh_watchlist_ticker(client, ticker="9999") -> None:
    create_resp = client.post(
        "/api/assets", json={"ticker": ticker, "name": "Test Co", "asset_type": "STOCK", "market": "TWSE", "currency": "TWD"}
    )
    assert create_resp.status_code == 201
    asset_id = create_resp.json()["id"]
    watchlist_resp = client.post("/api/watchlist", json={"asset_id": asset_id, "status": "WATCHING"})
    assert watchlist_resp.status_code == 201


def test_review_summary_is_null_hit_rate_before_anything_is_scored(client):
    resp = client.get("/api/review/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"hits": 0, "n": 0, "hit_rate": None}


def test_review_outcomes_is_empty_before_anything_is_scored(client):
    resp = client.get("/api/review/outcomes")
    assert resp.status_code == 200
    assert resp.json() == []


def test_full_round_trip_scores_an_outcome_after_enough_future_price_history_exists(client, stub_provider):
    """flat baseline -> uptrend creates a CONSIDER_INCREASE recommendation
    -> extending the uptrend 5+ more trading days lets the *next* Update
    Market Data run retroactively score that same recommendation."""
    add_fresh_watchlist_ticker(client, "9999")
    start = date.today() - timedelta(days=70)

    flat = [price_point(start + timedelta(days=i), "100") for i in range(65)]
    stub_provider.prices["9999"] = flat
    client.post("/api/market-data/update", params={"tickers": ["9999"]})  # NEUTRAL baseline

    rising = [price_point(start + timedelta(days=i), str(100 + i)) for i in range(65)]
    stub_provider.prices["9999"] = rising
    client.post("/api/market-data/update", params={"tickers": ["9999"]})  # creates CONSIDER_INCREASE

    # Not enough future history yet -- nothing scored.
    assert client.get("/api/review/outcomes").json() == []

    extended = [price_point(start + timedelta(days=i), str(100 + i)) for i in range(72)]
    stub_provider.prices["9999"] = extended
    client.post("/api/market-data/update", params={"tickers": ["9999"]})  # scores the earlier recommendation

    outcomes = client.get("/api/review/outcomes").json()
    assert len(outcomes) == 1
    assert outcomes[0]["ticker"] == "9999"
    assert outcomes[0]["action"] == "CONSIDER_INCREASE"
    assert outcomes[0]["call"] == "BULLISH"
    assert outcomes[0]["actual_direction"] == "BULLISH"
    assert outcomes[0]["hit"] is True

    summary = client.get("/api/review/summary").json()
    assert summary == {"hits": 1, "n": 1, "hit_rate": "1"}


def test_review_summary_action_filter(client, stub_provider):
    add_fresh_watchlist_ticker(client, "9999")
    start = date.today() - timedelta(days=70)

    flat = [price_point(start + timedelta(days=i), "100") for i in range(65)]
    stub_provider.prices["9999"] = flat
    client.post("/api/market-data/update", params={"tickers": ["9999"]})

    rising = [price_point(start + timedelta(days=i), str(100 + i)) for i in range(65)]
    stub_provider.prices["9999"] = rising
    client.post("/api/market-data/update", params={"tickers": ["9999"]})

    extended = [price_point(start + timedelta(days=i), str(100 + i)) for i in range(72)]
    stub_provider.prices["9999"] = extended
    client.post("/api/market-data/update", params={"tickers": ["9999"]})

    assert client.get("/api/review/summary?action=CONSIDER_INCREASE").json()["n"] == 1
    assert client.get("/api/review/summary?action=CONSIDER_DECREASE").json()["n"] == 0
