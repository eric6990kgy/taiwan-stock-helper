"""CSV import/export (PRD Sec.38, architecture decision A11)."""

import csv
import io


def _csv_bytes(rows: list[str]) -> bytes:
    return "\n".join(rows).encode("utf-8")


HEADER = "account_name,ticker,date,type,quantity,price,fee,tax,currency,note"


def test_export_transactions_contains_seeded_data(client):
    resp = client.get("/api/export/transactions")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(resp.text)))
    tickers = {r["ticker"] for r in rows}
    assert "3653" in tickers
    assert "GLOBAL-ETF-01" in tickers


def test_export_holdings_csv(client):
    resp = client.get("/api/export/holdings")
    assert resp.status_code == 200
    rows = list(csv.DictReader(io.StringIO(resp.text)))
    assert any(r["ticker"] == "3653" for r in rows)


def test_export_portfolio_snapshot_csv(client):
    resp = client.get("/api/export/portfolio-snapshot")
    assert resp.status_code == 200
    rows = list(csv.DictReader(io.StringIO(resp.text)))
    assert len(rows) == 1
    assert "remaining_cost_basis" in rows[0]


def test_import_transactions_creates_rows_and_flags_unknown_ticker(client):
    csv_text = _csv_bytes(
        [
            HEADER,
            "Fubon Securities,6002,2026-01-05,BUY,10,100,0,0,TWD,round trip test",
            "Fubon Securities,6002,2026-02-05,SELL,4,120,0,0,TWD,",
        ]
    )
    resp = client.post("/api/import/transactions", files={"file": ("txns.csv", csv_text, "text/csv")})
    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == 2
    assert body["skipped"] == []
    assert body["needs_review_tickers"] == ["6002"]

    asset = client.get("/api/assets/6002").json()
    assert asset["needs_review"] is True


def test_import_skips_unknown_account_with_reason(client):
    csv_text = _csv_bytes([HEADER, "Nonexistent Bank,3653,2026-01-05,BUY,10,100,0,0,TWD,"])
    resp = client.post("/api/import/transactions", files={"file": ("txns.csv", csv_text, "text/csv")})
    body = resp.json()
    assert body["imported"] == 0
    assert len(body["skipped"]) == 1
    assert "Unknown account" in body["skipped"][0]["reason"]


def test_import_skips_non_twd_currency_row(client):
    csv_text = _csv_bytes([HEADER, "Fubon Securities,3653,2026-01-05,BUY,10,100,0,0,USD,"])
    resp = client.post("/api/import/transactions", files={"file": ("txns.csv", csv_text, "text/csv")})
    body = resp.json()
    assert body["imported"] == 0
    assert "TWD" in body["skipped"][0]["reason"]


def test_import_skips_row_causing_insufficient_shares(client):
    csv_text = _csv_bytes([HEADER, "Fubon Securities,3491,2026-01-05,SELL,999,100,0,0,TWD,"])
    resp = client.post("/api/import/transactions", files={"file": ("txns.csv", csv_text, "text/csv")})
    body = resp.json()
    assert body["imported"] == 0
    assert "cannot sell" in body["skipped"][0]["reason"].lower()


def test_import_missing_required_column_returns_400(client):
    resp = client.post(
        "/api/import/transactions",
        files={"file": ("bad.csv", b"ticker,date\n3653,2026-01-01", "text/csv")},
    )
    assert resp.status_code == 400


def test_export_then_reimport_round_trip_produces_identical_holdings(client):
    """The full loop: import → export → delete → re-import the exported CSV
    → same resulting position. Proves the export format is faithfully
    re-importable, not just structurally similar."""
    fubon_id = next(a["id"] for a in client.get("/api/accounts").json() if a["name"] == "Fubon Securities")

    import_resp = client.post(
        "/api/import/transactions",
        files={
            "file": (
                "txns.csv",
                _csv_bytes(
                    [
                        HEADER,
                        "Fubon Securities,6003,2026-01-05,BUY,10,100,5,0,TWD,",
                        "Fubon Securities,6003,2026-03-05,BUY,10,120,5,0,TWD,",
                        "Fubon Securities,6003,2026-05-05,SELL,4,150,3,1,TWD,",
                    ]
                ),
                "text/csv",
            )
        },
    )
    assert import_resp.json()["imported"] == 3

    asset_id = client.get("/api/assets/6003").json()["id"]
    holdings_before = client.get(f"/api/holdings?account_id={fubon_id}").json()
    before = next(h for h in holdings_before if h["asset_id"] == asset_id)

    # Export, then pull out just this ticker's rows.
    export_text = client.get("/api/export/transactions").text
    all_rows = list(csv.DictReader(io.StringIO(export_text)))
    our_rows = [r for r in all_rows if r["ticker"] == "6003"]
    assert len(our_rows) == 3

    # Delete the 3 transactions we created (newest first -- SELL before BUYs
    # -- so the insufficient-shares replay check never trips mid-deletion).
    txns = client.get(f"/api/transactions?account_id={fubon_id}&asset_id={asset_id}").json()
    for txn in sorted(txns, key=lambda t: t["id"], reverse=True):
        assert client.delete(f"/api/transactions/{txn['id']}").status_code == 204

    holdings_after_delete = client.get(f"/api/holdings?account_id={fubon_id}").json()
    assert all(h["asset_id"] != asset_id for h in holdings_after_delete)

    # Re-import exactly the exported rows for this ticker.
    reimport_csv = "\n".join([HEADER] + [",".join(r[col] for col in HEADER.split(",")) for r in our_rows])
    reimport_resp = client.post(
        "/api/import/transactions", files={"file": ("reimport.csv", reimport_csv.encode("utf-8"), "text/csv")}
    )
    assert reimport_resp.json()["imported"] == 3
    assert reimport_resp.json()["needs_review_tickers"] == []  # asset 6003 already exists

    holdings_after_reimport = client.get(f"/api/holdings?account_id={fubon_id}").json()
    after = next(h for h in holdings_after_reimport if h["asset_id"] == asset_id)

    assert after["remaining_shares"] == before["remaining_shares"]
    assert after["average_cost"] == before["average_cost"]
    assert after["remaining_cost_basis"] == before["remaining_cost_basis"]
    assert after["realized_pnl"] == before["realized_pnl"]
