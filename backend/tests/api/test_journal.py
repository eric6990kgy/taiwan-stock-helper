"""Journal entry CRUD (Phase 10) -- append-only dated notes, optionally
tied to an asset/recommendation. See test_thesis.py for the deliberately
different one-row-per-asset upsert this does NOT reuse.
"""


def test_create_general_entry_with_no_asset(client):
    resp = client.post("/api/journal", json={"entry_date": "2026-01-10", "body": "Market felt choppy today."})
    assert resp.status_code == 201
    body = resp.json()
    assert body["asset_id"] is None
    assert body["ticker"] is None
    assert body["body"] == "Market felt choppy today."
    assert body["category"] == "OBSERVATION"  # default, never left unset


def test_create_entry_with_explicit_category(client):
    resp = client.post(
        "/api/journal", json={"entry_date": "2026-01-10", "category": "BUY_REASON", "body": "Bought on the dip."}
    )
    assert resp.status_code == 201
    assert resp.json()["category"] == "BUY_REASON"


def test_create_entry_invalid_category_422(client):
    resp = client.post("/api/journal", json={"entry_date": "2026-01-10", "category": "NOT_A_REAL_CATEGORY", "body": "x"})
    assert resp.status_code == 422


def test_list_entries_filters_by_category(client):
    client.post("/api/journal", json={"entry_date": "2026-01-10", "category": "BUY_REASON", "body": "Bought."})
    client.post("/api/journal", json={"entry_date": "2026-01-11", "category": "REVIEW", "body": "Reviewed."})

    resp = client.get("/api/journal?category=BUY_REASON")
    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) == 1
    assert entries[0]["body"] == "Bought."


def test_update_entry_category(client):
    created = client.post(
        "/api/journal", json={"entry_date": "2026-01-10", "category": "OBSERVATION", "body": "x"}
    ).json()
    resp = client.put(f"/api/journal/{created['id']}", json={"category": "REVIEW"})
    assert resp.status_code == 200
    assert resp.json()["category"] == "REVIEW"


def test_create_entry_tied_to_an_asset(client):
    asset_id = client.get("/api/assets/3653").json()["id"]
    resp = client.post("/api/journal", json={"entry_date": "2026-01-10", "asset_id": asset_id, "body": "Watching this one."})
    assert resp.status_code == 201
    body = resp.json()
    assert body["ticker"] == "3653"
    assert body["asset_name"] == "健策"


def test_create_entry_unknown_asset_404(client):
    resp = client.post("/api/journal", json={"entry_date": "2026-01-10", "asset_id": 999999, "body": "x"})
    assert resp.status_code == 404


def test_body_is_required(client):
    resp = client.post("/api/journal", json={"entry_date": "2026-01-10", "body": ""})
    assert resp.status_code == 422


def test_list_entries_filters_by_asset(client):
    asset_id = client.get("/api/assets/3653").json()["id"]
    client.post("/api/journal", json={"entry_date": "2026-01-10", "asset_id": asset_id, "body": "About 3653."})
    client.post("/api/journal", json={"entry_date": "2026-01-11", "body": "General note."})

    resp = client.get(f"/api/journal?asset_id={asset_id}")
    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) == 1
    assert entries[0]["body"] == "About 3653."


def test_list_entries_filters_by_date_range(client):
    client.post("/api/journal", json={"entry_date": "2026-01-01", "body": "Too early."})
    client.post("/api/journal", json={"entry_date": "2026-02-01", "body": "In range."})
    client.post("/api/journal", json={"entry_date": "2026-03-01", "body": "Too late."})

    resp = client.get("/api/journal?date_from=2026-01-15&date_to=2026-02-15")
    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) == 1
    assert entries[0]["body"] == "In range."


def test_update_entry_body(client):
    created = client.post("/api/journal", json={"entry_date": "2026-01-10", "body": "Draft."}).json()
    resp = client.put(f"/api/journal/{created['id']}", json={"body": "Final."})
    assert resp.status_code == 200
    assert resp.json()["body"] == "Final."


def test_update_unknown_entry_404(client):
    resp = client.put("/api/journal/999999", json={"body": "x"})
    assert resp.status_code == 404


def test_delete_entry(client):
    created = client.post("/api/journal", json={"entry_date": "2026-01-10", "body": "Delete me."}).json()
    resp = client.delete(f"/api/journal/{created['id']}")
    assert resp.status_code == 204
    assert client.get(f"/api/journal?asset_id=999999999").status_code == 200  # sanity: route still healthy
