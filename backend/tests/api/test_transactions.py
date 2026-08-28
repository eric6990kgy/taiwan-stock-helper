"""Transaction CRUD plus the two rules that only exist at the service layer:
TWD-only currency and insufficient-shares validation via app.analytics replay.
"""

from decimal import Decimal

import pytest


@pytest.fixture()
def fubon_account_id(client):
    accounts = client.get("/api/accounts").json()
    return next(a["id"] for a in accounts if a["name"] == "Fubon Securities")


@pytest.fixture()
def fresh_asset_id(client):
    """3491 has no seeded transactions -- a clean slate for tests that need
    to control the exact transaction history."""
    return client.get("/api/assets/3491").json()["id"]


def test_create_buy_transaction(client, fubon_account_id, fresh_asset_id):
    resp = client.post(
        "/api/transactions",
        json={
            "account_id": fubon_account_id,
            "asset_id": fresh_asset_id,
            "date": "2026-01-10",
            "type": "BUY",
            "quantity": "10",
            "price": "300",
            "fee": "40",
            "currency": "TWD",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    # Numeric(18,4)/(18,2) columns round-trip with their fixed scale.
    assert body["quantity"] == "10.0000"
    assert body["price"] == "300.0000"
    assert body["fee"] == "40.00"


def test_create_transaction_invalid_account_returns_404(client, fresh_asset_id):
    resp = client.post(
        "/api/transactions",
        json={
            "account_id": 999999,
            "asset_id": fresh_asset_id,
            "date": "2026-01-10",
            "type": "BUY",
            "quantity": "10",
            "price": "300",
            "currency": "TWD",
        },
    )
    assert resp.status_code == 404


def test_create_transaction_invalid_asset_returns_404(client, fubon_account_id):
    resp = client.post(
        "/api/transactions",
        json={
            "account_id": fubon_account_id,
            "asset_id": 999999,
            "date": "2026-01-10",
            "type": "BUY",
            "quantity": "10",
            "price": "300",
            "currency": "TWD",
        },
    )
    assert resp.status_code == 404


def test_create_transaction_rejects_non_twd_currency(client, fubon_account_id, fresh_asset_id):
    resp = client.post(
        "/api/transactions",
        json={
            "account_id": fubon_account_id,
            "asset_id": fresh_asset_id,
            "date": "2026-01-10",
            "type": "BUY",
            "quantity": "10",
            "price": "300",
            "currency": "USD",
        },
    )
    assert resp.status_code == 400
    assert "TWD" in resp.json()["detail"]


def test_create_transaction_rejects_zero_quantity(client, fubon_account_id, fresh_asset_id):
    resp = client.post(
        "/api/transactions",
        json={
            "account_id": fubon_account_id,
            "asset_id": fresh_asset_id,
            "date": "2026-01-10",
            "type": "BUY",
            "quantity": "0",
            "price": "300",
            "currency": "TWD",
        },
    )
    assert resp.status_code == 422  # caught by Pydantic's gt=0 constraint


def test_sell_more_than_held_returns_400(client, fubon_account_id, fresh_asset_id):
    client.post(
        "/api/transactions",
        json={
            "account_id": fubon_account_id,
            "asset_id": fresh_asset_id,
            "date": "2026-01-10",
            "type": "BUY",
            "quantity": "10",
            "price": "300",
            "currency": "TWD",
        },
    )
    resp = client.post(
        "/api/transactions",
        json={
            "account_id": fubon_account_id,
            "asset_id": fresh_asset_id,
            "date": "2026-02-10",
            "type": "SELL",
            "quantity": "15",
            "price": "320",
            "currency": "TWD",
        },
    )
    assert resp.status_code == 400
    assert "Cannot sell" in resp.json()["detail"]


def test_backdated_transaction_via_api_recalculates_realized_pnl(client, fubon_account_id, fresh_asset_id):
    """Mirrors the Phase 2 unit test but exercised through the live API +
    real DB round trip: enter BUY then SELL, then insert a backdated BUY
    between them, and confirm the holding's realized P&L updates to the
    date-sorted-correct value, not the insertion-order value."""
    client.post(
        "/api/transactions",
        json={
            "account_id": fubon_account_id,
            "asset_id": fresh_asset_id,
            "date": "2026-01-01",
            "type": "BUY",
            "quantity": "10",
            "price": "100",
            "currency": "TWD",
        },
    )
    client.post(
        "/api/transactions",
        json={
            "account_id": fubon_account_id,
            "asset_id": fresh_asset_id,
            "date": "2026-03-01",
            "type": "SELL",
            "quantity": "5",
            "price": "140",
            "currency": "TWD",
        },
    )
    # Backdated: actually happened 02-01, entered last.
    backdated = client.post(
        "/api/transactions",
        json={
            "account_id": fubon_account_id,
            "asset_id": fresh_asset_id,
            "date": "2026-02-01",
            "type": "BUY",
            "quantity": "10",
            "price": "120",
            "currency": "TWD",
        },
    )
    assert backdated.status_code == 201

    holdings = client.get(f"/api/holdings?account_id={fubon_account_id}").json()
    holding = next(h for h in holdings if h["asset_id"] == fresh_asset_id)

    # avg cost after both buys = 110; sell 5@140 -> cost sold 550, proceeds 700, realized 150
    assert holding["average_cost"] == "110.0000"
    assert Decimal(holding["realized_pnl"]) == Decimal("150")
    assert holding["remaining_shares"] == "15.0000"


def test_delete_transaction_that_would_break_later_sell_is_rejected(client, fubon_account_id, fresh_asset_id):
    buy = client.post(
        "/api/transactions",
        json={
            "account_id": fubon_account_id,
            "asset_id": fresh_asset_id,
            "date": "2026-01-01",
            "type": "BUY",
            "quantity": "10",
            "price": "100",
            "currency": "TWD",
        },
    ).json()
    client.post(
        "/api/transactions",
        json={
            "account_id": fubon_account_id,
            "asset_id": fresh_asset_id,
            "date": "2026-02-01",
            "type": "SELL",
            "quantity": "10",
            "price": "120",
            "currency": "TWD",
        },
    )
    resp = client.delete(f"/api/transactions/{buy['id']}")
    assert resp.status_code == 400


def test_get_update_delete_transaction(client, fubon_account_id, fresh_asset_id):
    created = client.post(
        "/api/transactions",
        json={
            "account_id": fubon_account_id,
            "asset_id": fresh_asset_id,
            "date": "2026-01-01",
            "type": "BUY",
            "quantity": "10",
            "price": "100",
            "currency": "TWD",
        },
    ).json()

    got = client.get(f"/api/transactions/{created['id']}")
    assert got.status_code == 200

    updated = client.put(f"/api/transactions/{created['id']}", json={"note": "updated note"})
    assert updated.status_code == 200
    assert updated.json()["note"] == "updated note"

    deleted = client.delete(f"/api/transactions/{created['id']}")
    assert deleted.status_code == 204
    assert client.get(f"/api/transactions/{created['id']}").status_code == 404


def test_list_transactions_filters_by_account_and_asset(client, fubon_account_id, fresh_asset_id):
    client.post(
        "/api/transactions",
        json={
            "account_id": fubon_account_id,
            "asset_id": fresh_asset_id,
            "date": "2026-01-01",
            "type": "BUY",
            "quantity": "10",
            "price": "100",
            "currency": "TWD",
        },
    )
    resp = client.get(f"/api/transactions?account_id={fubon_account_id}&asset_id={fresh_asset_id}")
    assert resp.status_code == 200
    assert all(t["account_id"] == fubon_account_id and t["asset_id"] == fresh_asset_id for t in resp.json())
