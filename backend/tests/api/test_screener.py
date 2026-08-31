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


# ---- Phase 6 P0 filters: foreign net buying / RSI / above-SMA20 -------------------


def test_screener_default_response_includes_phase6_fields_as_none_when_unavailable(client):
    """Seed data has no institutional-flow rows and only 11 days of price
    history (SMA20/RSI14 both need more) -- these fields must come back
    None, not a fabricated value, when nothing is filtered on them."""
    resp = client.get("/api/screener")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) > 0
    for r in rows:
        assert r["foreign_net_buy"] is None
        assert r["rsi_14"] is None
        assert r["above_sma_20"] is None


def test_screener_foreign_net_buy_filter_excludes_everything_when_no_institutional_data(client):
    resp = client.get("/api/screener?foreign_net_buy_gt=0")
    assert resp.status_code == 200
    assert resp.json() == []


def test_screener_above_sma_20_filter_excludes_everything_when_insufficient_history(client):
    resp = client.get("/api/screener?above_sma_20=true")
    assert resp.status_code == 200
    assert resp.json() == []


def test_screener_rsi_filter_excludes_everything_when_insufficient_history(client):
    resp = client.get("/api/screener?rsi_lt=70")
    assert resp.status_code == 200
    assert resp.json() == []


def test_screener_foreign_net_buy_filter_matches_once_data_is_ingested(client):
    """Directly seed one institutional-flow row (bypassing ingestion, same
    StaticPool-backed DB the client fixture uses) and confirm the filter
    picks it up."""
    from app.api.deps import get_db
    from app.main import app
    from app.repositories.asset_repository import AssetRepository
    from app.repositories.institutional_flow_repository import InstitutionalFlowRepository
    from datetime import date

    db = next(app.dependency_overrides[get_db]())
    asset = AssetRepository(db).get_by_ticker("3653")
    InstitutionalFlowRepository(db).upsert(asset.id, date(2026, 8, 28), foreign_net=5000, source="FINMIND")
    db.commit()
    db.close()

    resp = client.get("/api/screener?foreign_net_buy_gt=1000")
    assert resp.status_code == 200
    tickers = {r["ticker"] for r in resp.json()}
    assert "3653" in tickers
    matching = next(r for r in resp.json() if r["ticker"] == "3653")
    assert matching["foreign_net_buy"] == 5000

    resp_too_high = client.get("/api/screener?foreign_net_buy_gt=9999999")
    assert "3653" not in {r["ticker"] for r in resp_too_high.json()}
