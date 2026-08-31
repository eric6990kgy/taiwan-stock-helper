"""Contract test: MockMarketDataProvider and FinMindProvider both implement
MarketDataProvider and must behave consistently for the cases every caller
(services, ingestion) actually relies on -- same exception types for the
same situations, same DTO shapes. This is what lets app/api/deps.py swap
providers without touching anything above it (architecture Sec.31).
"""

from datetime import date
from decimal import Decimal

import httpx
import pytest

from app.database.seed import seed
from app.providers.finmind_provider import FinMindProvider
from app.providers.market_data_provider import AssetNotFoundError, MarketDataProvider
from app.providers.mock_provider import MockMarketDataProvider

ALL_PROVIDER_METHODS = (
    "get_quote",
    "get_historical_prices",
    "get_fundamentals",
    "get_company_info",
    "get_dividends",
    "get_valuation",
    "get_institutional_flows",
    "get_margin_trading",
    "get_monthly_revenue",
)


def test_both_providers_are_concrete_implementations():
    """Both classes must actually satisfy the ABC -- if either were missing
    a method, instantiating it would raise TypeError."""
    assert issubclass(MockMarketDataProvider, MarketDataProvider)
    assert issubclass(FinMindProvider, MarketDataProvider)
    for method in ALL_PROVIDER_METHODS:
        assert hasattr(MockMarketDataProvider, method)
        assert hasattr(FinMindProvider, method)


def test_mock_provider_raises_asset_not_found_for_unknown_ticker(db_session):
    seed(db_session)
    provider = MockMarketDataProvider(db_session)
    with pytest.raises(AssetNotFoundError):
        provider.get_quote("NOPE")


def test_finmind_provider_raises_asset_not_found_for_unknown_ticker():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"msg": "success", "status": 200, "data": []})

    provider = FinMindProvider(client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(AssetNotFoundError):
        provider.get_quote("NOPE")


def test_mock_provider_quote_dto_shape_matches_finmind_quote_dto_shape(db_session):
    """Both providers' get_quote() must return the same DTO type with the
    same field types -- this is what makes them interchangeable."""
    seed(db_session)
    mock_provider = MockMarketDataProvider(db_session)
    mock_quote = mock_provider.get_quote("3653")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "msg": "success",
                "status": 200,
                "data": [{"date": "2026-08-28", "stock_id": "3653", "Trading_Volume": 1, "Trading_money": 1, "open": 1, "max": 1, "min": 1, "close": 100, "spread": 0, "Trading_turnover": 1}],
            },
        )

    finmind_provider = FinMindProvider(client=httpx.Client(transport=httpx.MockTransport(handler)))
    finmind_quote = finmind_provider.get_quote("3653")

    assert type(mock_quote) is type(finmind_quote)
    assert isinstance(mock_quote.price, Decimal) and isinstance(finmind_quote.price, Decimal)
    assert isinstance(mock_quote.as_of, date) and isinstance(finmind_quote.as_of, date)
