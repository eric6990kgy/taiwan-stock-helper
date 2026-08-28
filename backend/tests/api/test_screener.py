def test_screener_with_no_filters_returns_all_stocks_and_etfs(client):
    resp = client.get("/api/screener")
    assert resp.status_code == 200
    tickers = {r["ticker"] for r in resp.json()}
    assert "3653" in tickers
    assert "GLOBAL-ETF-01" not in tickers  # asset_type=FUND, not STOCK/ETF


def test_screener_roe_filter(client):
    # Seed data gives every TW stock roe=0.18 (18%).
    resp = client.get("/api/screener?roe_gt=15")
    assert resp.status_code == 200
    assert len(resp.json()) == 7
    resp_none = client.get("/api/screener?roe_gt=50")
    assert resp_none.json() == []


def test_screener_pe_filter(client):
    resp = client.get("/api/screener?pe_lt=1000")
    assert resp.status_code == 200
    assert len(resp.json()) > 0
    for r in resp.json():
        assert r["pe_ratio"] is not None


def test_screener_market_cap_filter_returns_400(client):
    """A11-adjacent decision from the Phase 3 kickoff: don't invent a
    market-cap/dividend-yield calculation the schema can't actually support."""
    resp = client.get("/api/screener?market_cap_gt=1000000000")
    assert resp.status_code == 400


def test_screener_revenue_growth_filter_returns_none_matches_with_single_period_seed_data(client):
    """The seed data only has one TTM fundamentals period per stock, so YoY
    growth can't be computed -- this must return an empty (honest) result,
    not a fabricated number."""
    resp = client.get("/api/screener?revenue_growth_gt=0")
    assert resp.status_code == 200
    assert resp.json() == []


def test_screener_never_returns_a_buy_sell_verdict(client):
    resp = client.get("/api/screener")
    for r in resp.json():
        assert "buy" not in r
        assert "sell" not in r
        assert r["meets_criteria"] is True
