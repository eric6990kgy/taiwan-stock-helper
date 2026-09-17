import pytest


def test_list_assets_returns_seeded_assets(client):
    resp = client.get("/api/assets")
    assert resp.status_code == 200
    tickers = {a["ticker"] for a in resp.json()}
    assert "3653" in tickers
    assert "GLOBAL-ETF-01" in tickers


def test_list_assets_excludes_index_assets(client):
    """TAIEX (asset_type=INDEX, Phase 7 regime-detection bookkeeping) must
    never appear in this endpoint -- it feeds every ticker/asset picker in
    the frontend (Research, Watchlist, Transactions), and TAIEX is never a
    real holding or research target."""
    from app.api.deps import get_db
    from app.main import app
    from app.repositories.asset_repository import AssetRepository

    db = next(app.dependency_overrides[get_db]())
    AssetRepository(db).create(ticker="TAIEX", name="TAIEX", asset_type="INDEX", currency="TWD", is_demo_data=False)
    db.commit()
    db.close()

    resp = client.get("/api/assets")
    assert resp.status_code == 200
    tickers = {a["ticker"] for a in resp.json()}
    assert "TAIEX" not in tickers


def test_get_asset_by_ticker(client):
    resp = client.get("/api/assets/3653")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "健策"
    assert body["is_demo_data"] is True


def test_get_asset_unknown_ticker_404(client):
    resp = client.get("/api/assets/NOPE")
    assert resp.status_code == 404


def test_create_asset(client):
    resp = client.post(
        "/api/assets",
        json={"ticker": "9999", "name": "Test Co", "asset_type": "STOCK", "currency": "TWD"},
    )
    assert resp.status_code == 201
    assert resp.json()["ticker"] == "9999"
    assert resp.json()["valuation_method"] == "TRANSACTION_BASED"  # default
    assert resp.json()["needs_review"] is False  # default


def test_create_asset_duplicate_ticker_returns_409(client):
    payload = {"ticker": "3653", "name": "Duplicate", "asset_type": "STOCK", "currency": "TWD"}
    resp = client.post("/api/assets", json=payload)
    assert resp.status_code == 409


def test_create_asset_invalid_asset_type_422(client):
    resp = client.post(
        "/api/assets", json={"ticker": "AAAA", "name": "Bad", "asset_type": "CRYPTO", "currency": "TWD"}
    )
    assert resp.status_code == 422


def test_update_asset(client):
    created = client.post(
        "/api/assets", json={"ticker": "8888", "name": "Before", "asset_type": "STOCK", "currency": "TWD"}
    ).json()
    resp = client.put(f"/api/assets/{created['id']}", json={"name": "After"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "After"


def test_delete_asset(client):
    created = client.post(
        "/api/assets", json={"ticker": "7777", "name": "Delete Me", "asset_type": "STOCK", "currency": "TWD"}
    ).json()
    resp = client.delete(f"/api/assets/{created['id']}")
    assert resp.status_code == 204


class _StubProvider:
    """Phase 11: a minimal stand-in for FinMindProvider, implementing only
    get_company_info/get_historical_prices (what quick-create actually
    calls) -- same pattern as test_recommendations.py's/test_review.py's
    StubProvider, scoped to just what this test file needs."""

    def __init__(self):
        self.company_info = {}
        self.prices = {}

    def get_company_info(self, ticker):
        from app.providers.market_data_provider import AssetNotFoundError

        if ticker not in self.company_info:
            raise AssetNotFoundError(ticker)
        return self.company_info[ticker]

    def get_historical_prices(self, ticker, start=None, end=None):
        return self.prices.get(ticker, [])

    def get_valuation(self, ticker, on_date=None):
        from app.providers.market_data_provider import AssetNotFoundError

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


@pytest.fixture()
def stub_provider(client):
    from app.api.deps import get_finmind_provider
    from app.main import app

    provider = _StubProvider()

    def override():
        yield provider

    app.dependency_overrides[get_finmind_provider] = override
    yield provider
    app.dependency_overrides.pop(get_finmind_provider, None)


def _company_info(ticker: str, name: str, market: str = "TWSE") -> "CompanyInfoDTO":
    from app.providers.market_data_provider import CompanyInfoDTO

    return CompanyInfoDTO(
        ticker=ticker, name=name, asset_type="STOCK", market=market, sector=None, industry=None, is_demo_data=False
    )


def _price_point(d, close: str):
    from decimal import Decimal

    from app.providers.market_data_provider import PricePointDTO

    c = Decimal(close)
    return PricePointDTO(date=d, open=c, high=c, low=c, close=c, volume=1000, source="FINMIND")


def test_lookup_ticker_returns_finmind_company_info(client, stub_provider):
    stub_provider.company_info["2330"] = _company_info("2330", "台積電")

    resp = client.get("/api/assets/lookup/2330")

    assert resp.status_code == 200
    body = resp.json()
    assert body == {
        "ticker": "2330", "name": "台積電", "asset_type": "STOCK", "market": "TWSE",
        "sector": None, "industry": None,
    }


def test_lookup_unknown_ticker_404(client, stub_provider):
    resp = client.get("/api/assets/lookup/NOPE")
    assert resp.status_code == 404


def test_quick_create_creates_asset_with_looked_up_fields(client, stub_provider):
    stub_provider.company_info["2330"] = _company_info("2330", "台積電")

    resp = client.post("/api/assets/quick-create", json={"ticker": "2330"})

    assert resp.status_code == 201
    body = resp.json()
    assert body["ticker"] == "2330"
    assert body["name"] == "台積電"
    assert body["market"] == "TWSE"
    assert body["valuation_method"] == "TRANSACTION_BASED"


def test_quick_create_backfills_price_history_immediately(client, stub_provider):
    from datetime import date

    stub_provider.company_info["2330"] = _company_info("2330", "台積電")
    stub_provider.prices["2330"] = [_price_point(date(2026, 9, 15), "600")]

    created = client.post("/api/assets/quick-create", json={"ticker": "2330"}).json()

    prices = client.get(f"/api/prices/2330").json()
    assert len(prices) == 1
    assert prices[0]["close"] == "600.0000"


def test_quick_create_unknown_ticker_404(client, stub_provider):
    resp = client.post("/api/assets/quick-create", json={"ticker": "NOPE"})
    assert resp.status_code == 404


def test_quick_create_duplicate_ticker_returns_409(client, stub_provider):
    stub_provider.company_info["3653"] = _company_info("3653", "健策")
    resp = client.post("/api/assets/quick-create", json={"ticker": "3653"})
    assert resp.status_code == 409


def test_delete_asset_with_transactions_is_blocked(client):
    """Asset.transactions carries the same ORM cascade="all, delete-orphan"
    as Account.transactions -- unguarded, deleting the asset would silently
    destroy every transaction against it. See test_accounts.py's equivalent
    test for the incident this pattern caused on the account side."""
    asset = client.post(
        "/api/assets", json={"ticker": "6666", "name": "Has Transactions", "asset_type": "STOCK", "currency": "TWD"}
    ).json()
    account_id = client.get("/api/accounts").json()[0]["id"]
    txn = client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "asset_id": asset["id"],
            "date": "2026-01-10",
            "type": "BUY",
            "quantity": "10",
            "price": "300",
            "fee": "40",
            "currency": "TWD",
        },
    ).json()

    resp = client.delete(f"/api/assets/{asset['id']}")

    assert resp.status_code == 400
    assert "still has transactions" in resp.json()["detail"].lower()
    assert client.get(f"/api/assets/{asset['ticker']}").status_code == 200  # this route is keyed by ticker, not id
    assert client.get(f"/api/transactions/{txn['id']}").status_code == 200
