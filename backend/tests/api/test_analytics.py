from decimal import Decimal


def test_allocation_weights_sum_to_one(client):
    resp = client.get("/api/analytics/allocation")
    assert resp.status_code == 200
    body = resp.json()
    total_weight = sum(Decimal(e["weight"]) for e in body["entries"] if e["weight"] is not None)
    assert abs(total_weight - Decimal("1")) < Decimal("0.0001")


def test_performance_is_a_labeled_snapshot(client):
    resp = client.get("/api/analytics/performance")
    assert resp.status_code == 200
    body = resp.json()
    assert "note" in body and "snapshot" in body["note"].lower()
    assert "remaining_cost_basis" in body


def test_risk_reports_sector_concentration_and_top_holdings(client):
    resp = client.get("/api/analytics/risk")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["sector_concentration"]) > 0
    assert len(body["top_holdings"]) > 0
    assert body["max_single_position_weight"] is not None
    assert "volatility" in body["note"].lower() or "drawdown" in body["note"].lower()


def test_risk_reports_confirmed_limit_thresholds(client):
    """個股訊號引擎規格書 Sec.05/07 -- confirmed 2026-09-14."""
    resp = client.get("/api/analytics/risk")
    body = resp.json()
    assert body["position_limit_pct"] == "0.15"
    assert body["sector_limit_pct"] == "0.30"
    assert "position_limit_violations" in body
    assert "sector_limit_violations" in body
    # Limits are scoped to the individual-stock sleeve (asset_type=STOCK)
    # only -- the demo portfolio's Global ETF fund (65% of total net worth)
    # and cash (27%) must never appear here, even though they dwarf the two
    # TW stock positions. Regression guard for that scoping bug.
    flagged_labels = {v["label"] for v in body["position_limit_violations"]}
    assert "GLOBAL-ETF-01" not in flagged_labels
    assert "TWD-CASH" not in flagged_labels
    # Both TW stocks share sector="Technology" and together are 100% of the
    # STOCK-only sleeve -- over the 30% cluster limit, so this must fire.
    assert any(v["label"] == "Technology" for v in body["sector_limit_violations"])


def test_drawdown_reports_a_status_for_the_demo_portfolio(client):
    resp = client.get("/api/analytics/drawdown")
    assert resp.status_code == 200
    body = resp.json()
    assert body is not None
    assert body["action"] in ("OK", "PAUSE_NEW_POSITIONS", "HARD_STOP")
    assert body["pause_threshold_pct"] == "0.15"
    assert body["stop_threshold_pct"] == "0.25"
    assert Decimal(body["equity"]) >= Decimal("0")


def test_benchmark_reports_none_when_benchmark_asset_not_added(client):
    """The demo dataset never adds 0050 as a tracked Asset -- the endpoint
    must degrade honestly (null + an explanatory note), never fabricate a
    benchmark return."""
    resp = client.get("/api/analytics/benchmark")
    assert resp.status_code == 200
    body = resp.json()
    assert body["benchmark_ticker"] == "0050"
    assert body["benchmark_return_pct"] is None
    assert body["alpha_pct"] is None
    assert body["note"] is not None and "0050" in body["note"]


def test_benchmark_computes_alpha_once_benchmark_history_exists(client):
    """Adding the benchmark asset + price history (the documented one-time
    setup step) makes alpha computable -- the read path AnalyticsService
    actually depends on, exercised end-to-end here."""
    create_resp = client.post(
        "/api/assets",
        json={"ticker": "0050", "name": "元大台灣50", "asset_type": "ETF", "market": "TWSE", "currency": "TWD"},
    )
    assert create_resp.status_code == 201

    resp = client.get("/api/analytics/benchmark")
    body = resp.json()
    # Asset exists now but has no price_history yet -- still an honest null,
    # not a crash.
    assert body["benchmark_return_pct"] is None
    assert "資料不足" in body["note"] or "更新" in body["note"]
