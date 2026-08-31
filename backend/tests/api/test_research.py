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


# ---- Phase 6: institutional flow / margin / revenue / technical -----------------


def test_institutional_endpoint_returns_empty_list_when_no_data_ingested_yet(client):
    """The seed dataset predates Phase 6 -- no institutional rows exist for
    3653 yet. An honest empty list, not a fabricated row or a 500."""
    resp = client.get("/api/research/3653/institutional")
    assert resp.status_code == 200
    assert resp.json() == []


def test_institutional_endpoint_unknown_ticker_404(client):
    resp = client.get("/api/research/NOPE/institutional")
    assert resp.status_code == 404


def test_margin_endpoint_returns_empty_list_when_no_data_ingested_yet(client):
    resp = client.get("/api/research/3653/margin")
    assert resp.status_code == 200
    assert resp.json() == []


def test_revenue_endpoint_returns_empty_list_when_no_data_ingested_yet(client):
    resp = client.get("/api/research/3653/revenue")
    assert resp.status_code == 200
    assert resp.json() == []


def test_revenue_endpoint_computes_yoy_and_mom_growth(client):
    """Seed a couple of monthly-revenue rows directly via the repository
    (the seed dataset itself has none) and confirm growth is computed on
    read, with a missing comparison period coming back None, not 0%."""
    from decimal import Decimal

    from app.api.deps import get_db
    from app.main import app
    from app.repositories.asset_repository import AssetRepository
    from app.repositories.monthly_revenue_repository import MonthlyRevenueRepository

    # StaticPool backs the client fixture's in-memory DB, so a session opened
    # through the same dependency-override generator sees/persists into it.
    db = next(app.dependency_overrides[get_db]())
    asset = AssetRepository(db).get_by_ticker("3653")
    repo = MonthlyRevenueRepository(db)
    repo.upsert(asset.id, 2025, 7, revenue=Decimal("100"), source="FINMIND")
    repo.upsert(asset.id, 2026, 6, revenue=Decimal("90"), source="FINMIND")
    repo.upsert(asset.id, 2026, 7, revenue=Decimal("120"), source="FINMIND")
    db.commit()
    db.close()

    resp = client.get("/api/research/3653/revenue")
    assert resp.status_code == 200
    rows = {(r["revenue_year"], r["revenue_month"]): r for r in resp.json()}

    latest = rows[(2026, 7)]
    assert latest["yoy_growth"] == str((Decimal("120") - Decimal("100")) / Decimal("100"))
    assert latest["mom_growth"] == str((Decimal("120") - Decimal("90")) / Decimal("90"))

    earliest = rows[(2025, 7)]
    assert earliest["yoy_growth"] is None  # no 2024-07 comparison row exists
    assert earliest["mom_growth"] is None  # no 2025-06 comparison row exists


def test_technical_endpoint_returns_calculated_indicators(client):
    resp = client.get("/api/research/3653/technical")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ticker"] == "3653"
    assert body["source"] == "CALCULATED"
    assert body["as_of"] is not None
    # 11 seeded price points: enough for SMA(5) but not SMA(20)/MACD(26).
    assert body["indicators"]["sma_5"] is not None
    assert body["indicators"]["sma_20"] is None
    assert body["indicators"]["macd"] is None


def test_technical_endpoint_unknown_ticker_404(client):
    resp = client.get("/api/research/NOPE/technical")
    assert resp.status_code == 404


def test_technical_endpoint_as_of_truncates_to_historical_snapshot(client):
    """as_of lets a caller ask "what did the indicators look like on date X"
    -- must never use price rows after that date (Sec.12: no look-ahead)."""
    full = client.get("/api/research/3653/technical").json()
    earlier = client.get("/api/research/3653/technical?as_of=2026-08-20").json()

    assert earlier["as_of"] <= "2026-08-20"
    assert earlier["as_of"] != full["as_of"]
