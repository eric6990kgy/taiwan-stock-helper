"""End-to-end: create a transaction through the API and confirm it flows
through to /api/portfolio and /api/holdings, Decimal-exact, with no
handwritten math on the test side beyond what the fixture already knows."""

from decimal import Decimal

import pytest


@pytest.fixture()
def fubon_account_id(client):
    accounts = client.get("/api/accounts").json()
    return next(a["id"] for a in accounts if a["name"] == "Fubon Securities")


@pytest.fixture()
def fresh_asset_id(client):
    return client.get("/api/assets/3491").json()["id"]


def test_transaction_flows_through_to_holdings_and_portfolio(client, fubon_account_id, fresh_asset_id):
    before = client.get("/api/portfolio").json()

    client.post(
        "/api/transactions",
        json={
            "account_id": fubon_account_id,
            "asset_id": fresh_asset_id,
            "date": "2026-01-01",
            "type": "BUY",
            "quantity": "20",
            "price": "300",
            "fee": "50",
            "currency": "TWD",
        },
    )

    after = client.get("/api/portfolio").json()
    # 20*300 + 50 = 6050 added to remaining cost basis
    assert Decimal(after["remaining_cost_basis"]) - Decimal(before["remaining_cost_basis"]) == Decimal("6050")

    holdings = client.get(f"/api/holdings?account_id={fubon_account_id}").json()
    holding = next(h for h in holdings if h["asset_id"] == fresh_asset_id)
    assert holding["remaining_shares"] == "20.0000"
    assert holding["average_cost"] == "302.5000"
    assert Decimal(holding["remaining_cost_basis"]) == Decimal("6050")
    assert holding["ticker"] == "3491"


def test_decimal_fields_serialize_as_strings_not_floats(client):
    resp = client.get("/api/portfolio")
    body = resp.json()
    for field in ["total_market_value", "remaining_cost_basis", "realized_pnl", "unrealized_pnl", "total_pnl"]:
        assert isinstance(body[field], str), f"{field} should serialize as a string, got {type(body[field])}"
        Decimal(body[field])  # must parse cleanly as an exact Decimal


def test_manual_market_value_fund_shows_correct_market_value_via_api(client):
    holdings = client.get("/api/holdings").json()
    fund = next(h for h in holdings if h["ticker"] == "GLOBAL-ETF-01")

    assert fund["valuation_method"] == "MANUAL_MARKET_VALUE"
    # Seed: deposited 120000 (quantity=amount, price=1), latest manual valuation 120000.
    assert fund["remaining_shares"] == "120000.0000"
    assert fund["remaining_cost_basis"] == "120000.00000000"
    assert fund["market_value"] == "120000.0000"  # latest_close taken directly, NOT shares x price
    assert Decimal(fund["unrealized_pnl"]) == Decimal("0")


def test_portfolio_summary_field_naming_matches_architecture_decision(client):
    """Explicit instruction from Phase 3 kickoff: never expose the engine's
    remaining-cost-basis figure as `invested_capital`, and never invent
    `lifetime_contributions`."""
    body = client.get("/api/portfolio").json()
    assert "remaining_cost_basis" in body
    assert "invested_capital" not in body
    assert "lifetime_contributions" not in body


def test_holdings_only_lists_open_positions(client, fubon_account_id, fresh_asset_id):
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
            "date": "2026-02-01",
            "type": "SELL",
            "quantity": "10",
            "price": "120",
            "currency": "TWD",
        },
    )
    holdings = client.get(f"/api/holdings?account_id={fubon_account_id}").json()
    assert all(h["asset_id"] != fresh_asset_id for h in holdings)

    # But realized P&L from the now-closed position still counts in the summary.
    summary = client.get("/api/portfolio").json()
    assert Decimal(summary["realized_pnl"]) >= Decimal("200")  # (120-100)*10 = 200, plus whatever seed already had
