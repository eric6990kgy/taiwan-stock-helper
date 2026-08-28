def test_list_assets_returns_seeded_assets(client):
    resp = client.get("/api/assets")
    assert resp.status_code == 200
    tickers = {a["ticker"] for a in resp.json()}
    assert "3653" in tickers
    assert "GLOBAL-ETF-01" in tickers


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
