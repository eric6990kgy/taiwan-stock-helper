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
