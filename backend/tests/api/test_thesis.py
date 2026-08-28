def test_get_thesis_for_seeded_ticker(client):
    resp = client.get("/api/thesis/3653")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "INTACT"
    assert len(body["key_metrics"]) == 3


def test_get_thesis_for_ticker_with_no_thesis_returns_404(client):
    resp = client.get("/api/thesis/3515")
    assert resp.status_code == 404


def test_get_thesis_for_unknown_ticker_returns_404(client):
    resp = client.get("/api/thesis/NOPE")
    assert resp.status_code == 404


def test_upsert_creates_thesis_on_first_write(client):
    resp = client.put(
        "/api/thesis/3515",
        json={
            "thesis": "Motherboard demand recovering with AI PC cycle.",
            "status": "NEEDS_REVIEW",
            "key_metrics": [{"label": "Revenue Growth", "operator": ">", "value": 10}],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ticker"] == "3515"
    assert body["status"] == "NEEDS_REVIEW"

    # Second call updates the same row rather than creating a duplicate.
    resp2 = client.put("/api/thesis/3515", json={"thesis": "Updated.", "status": "INTACT"})
    assert resp2.status_code == 200
    assert resp2.json()["id"] == body["id"]
    assert resp2.json()["thesis"] == "Updated."
