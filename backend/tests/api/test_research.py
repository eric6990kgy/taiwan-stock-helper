def test_research_page_bundles_profile_quote_fundamentals_and_thesis(client):
    resp = client.get("/api/research/3653")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "健策"
    assert body["quote"]["price"] == "650.0000"
    assert body["latest_fundamentals"]["period"] == "TTM"
    assert body["thesis"]["status"] == "INTACT"


def test_research_page_thesis_is_none_when_not_set(client):
    resp = client.get("/api/research/3515")
    assert resp.status_code == 200
    assert resp.json()["thesis"] is None


def test_research_page_unknown_ticker_404(client):
    resp = client.get("/api/research/NOPE")
    assert resp.status_code == 404


def test_fundamentals_endpoint(client):
    resp = client.get("/api/fundamentals/3653")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["period"] == "TTM"
    assert rows[0]["source"] == "MOCK"


def test_prices_endpoint_returns_full_history_with_no_range(client):
    resp = client.get("/api/prices/3653")
    assert resp.status_code == 200
    assert len(resp.json()) == 11  # seeded 10 days back + today


def test_prices_endpoint_respects_range_param(client):
    resp = client.get("/api/prices/3653?range=1M")
    assert resp.status_code == 200
    assert len(resp.json()) == 11  # all seeded points fall within 1M of the latest date


def test_prices_endpoint_invalid_range_returns_400(client):
    resp = client.get("/api/prices/3653?range=10Y")
    assert resp.status_code == 400
