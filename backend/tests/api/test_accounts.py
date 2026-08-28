def test_list_accounts_returns_seeded_accounts(client):
    resp = client.get("/api/accounts")
    assert resp.status_code == 200
    names = {a["name"] for a in resp.json()}
    assert names == {"Fubon Securities", "Global ETF Account", "Cash"}


def test_create_account(client):
    resp = client.post("/api/accounts", json={"name": "Test Broker", "account_type": "BROKERAGE", "currency": "TWD"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Test Broker"
    assert body["account_type"] == "BROKERAGE"
    assert "id" in body and "user_id" in body


def test_create_account_rejects_invalid_account_type(client):
    resp = client.post("/api/accounts", json={"name": "Bad", "account_type": "CRYPTO_WALLET", "currency": "TWD"})
    assert resp.status_code == 422  # Pydantic pattern validation


def test_get_account_by_id(client):
    created = client.post("/api/accounts", json={"name": "Lookup Me", "account_type": "BANK", "currency": "TWD"}).json()
    resp = client.get(f"/api/accounts/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Lookup Me"


def test_get_account_not_found(client):
    resp = client.get("/api/accounts/999999")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_update_account(client):
    created = client.post("/api/accounts", json={"name": "Old Name", "account_type": "BANK", "currency": "TWD"}).json()
    resp = client.put(f"/api/accounts/{created['id']}", json={"name": "New Name"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"


def test_delete_account(client):
    created = client.post("/api/accounts", json={"name": "Delete Me", "account_type": "BANK", "currency": "TWD"}).json()
    resp = client.delete(f"/api/accounts/{created['id']}")
    assert resp.status_code == 204
    assert client.get(f"/api/accounts/{created['id']}").status_code == 404
