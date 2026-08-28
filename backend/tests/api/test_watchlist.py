def test_list_watchlist_includes_seeded_entry(client):
    resp = client.get("/api/watchlist")
    assert resp.status_code == 200
    tickers = {w["ticker"] for w in resp.json()}
    assert "3491" in tickers


def test_create_watchlist_entry(client):
    asset_id = client.get("/api/assets/3515").json()["id"]
    resp = client.post(
        "/api/watchlist",
        json={
            "asset_id": asset_id,
            "status": "WATCHING",
            "reason": "Motherboard demand recovery",
            "target_metrics": {"roe_gt": 10},
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["ticker"] == "3515"
    assert body["target_metrics"] == {"roe_gt": 10}


def test_create_duplicate_watchlist_entry_returns_409(client):
    asset_id = client.get("/api/assets/3491").json()["id"]  # already on watchlist from seed
    resp = client.post("/api/watchlist", json={"asset_id": asset_id, "status": "WATCHING"})
    assert resp.status_code == 409


def test_create_watchlist_entry_unknown_asset_returns_404(client):
    resp = client.post("/api/watchlist", json={"asset_id": 999999, "status": "WATCHING"})
    assert resp.status_code == 404


def test_update_watchlist_entry(client):
    entries = client.get("/api/watchlist").json()
    entry = entries[0]
    resp = client.put(f"/api/watchlist/{entry['id']}", json={"status": "CANDIDATE"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "CANDIDATE"


def test_delete_watchlist_entry(client):
    asset_id = client.get("/api/assets/3563").json()["id"]
    created = client.post("/api/watchlist", json={"asset_id": asset_id, "status": "WATCHING"}).json()
    resp = client.delete(f"/api/watchlist/{created['id']}")
    assert resp.status_code == 204


def test_filter_watchlist_by_status(client):
    resp = client.get("/api/watchlist?status=RESEARCHING")
    assert resp.status_code == 200
    assert all(w["status"] == "RESEARCHING" for w in resp.json())
