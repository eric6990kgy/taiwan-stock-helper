"""CSV import/export (PRD Sec.38). Import deliberately delegates each row to
TransactionService.create() rather than inserting rows directly — that's
the only place account/asset existence, TWD-only currency, and the
insufficient-shares replay check live, and a bulk importer is exactly the
kind of caller that must not bypass them (A11's whole premise is "never
silently drop rows" — reusing the service guarantees the same rules apply
whether a transaction comes from the API or a CSV).
"""

import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.repositories.account_repository import AccountRepository
from app.repositories.asset_repository import AssetRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.import_export import ImportResult, ImportSkippedRow
from app.services.exceptions import DuplicateError, NotFoundError, UnsupportedCurrencyError
from app.services.portfolio_service import PortfolioService
from app.services.transaction_service import TransactionService

TRANSACTION_CSV_COLUMNS = ["account_name", "ticker", "date", "type", "quantity", "price", "fee", "tax", "currency", "note"]


class ImportExportService:
    def __init__(self, db: Session):
        self.db = db
        self.accounts = AccountRepository(db)
        self.assets = AssetRepository(db)
        self.transactions = TransactionRepository(db)
        self.transaction_service = TransactionService(db)

    # ---- Import -------------------------------------------------------------

    def import_transactions(self, csv_text: str) -> ImportResult:
        reader = csv.DictReader(io.StringIO(csv_text))
        missing = set(TRANSACTION_CSV_COLUMNS) - {"note"} - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV is missing required column(s): {sorted(missing)}")

        imported = 0
        skipped: list[ImportSkippedRow] = []
        needs_review_tickers: list[str] = []

        for row_num, row in enumerate(reader, start=1):
            try:
                account_name = (row.get("account_name") or "").strip()
                ticker = (row.get("ticker") or "").strip()
                if not account_name or not ticker:
                    raise ValueError("account_name and ticker are required.")

                account = next(
                    (a for a in self.accounts.list() if a.name.strip().lower() == account_name.lower()), None
                )
                if account is None:
                    raise NotFoundError(f"Unknown account: {account_name!r}")

                asset = self.assets.get_by_ticker(ticker)
                if asset is None:
                    asset = self.assets.create(
                        ticker=ticker,
                        name=ticker,
                        asset_type="STOCK",
                        currency="TWD",
                        valuation_method="TRANSACTION_BASED",
                        is_demo_data=False,
                        needs_review=True,
                    )
                    needs_review_tickers.append(ticker)

                txn_date = date.fromisoformat(row["date"].strip())
                self.transaction_service.create(
                    account_id=account.id,
                    asset_id=asset.id,
                    date=txn_date,
                    type=row["type"].strip(),
                    quantity=Decimal(row["quantity"].strip()),
                    price=Decimal(row["price"].strip()),
                    fee=Decimal((row.get("fee") or "0").strip() or "0"),
                    tax=Decimal((row.get("tax") or "0").strip() or "0"),
                    currency=(row.get("currency") or "TWD").strip(),
                    note=(row.get("note") or "").strip() or None,
                )
                imported += 1

            except (ValueError, InvalidOperation, NotFoundError, UnsupportedCurrencyError, DuplicateError) as exc:
                skipped.append(ImportSkippedRow(row=row_num, reason=str(exc)))

        return ImportResult(imported=imported, skipped=skipped, needs_review_tickers=needs_review_tickers)

    # ---- Export ---------------------------------------------------------------

    def export_transactions_csv(self) -> str:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(TRANSACTION_CSV_COLUMNS)
        for txn in self.transactions.list_all():
            account = self.accounts.get(txn.account_id)
            asset = self.assets.get(txn.asset_id)
            writer.writerow(
                [
                    account.name,
                    asset.ticker,
                    txn.date.isoformat(),
                    txn.type,
                    str(txn.quantity),
                    str(txn.price),
                    str(txn.fee),
                    str(txn.tax),
                    txn.currency,
                    txn.note or "",
                ]
            )
        return buf.getvalue()

    def export_holdings_csv(self, market_data) -> str:
        portfolio_service = PortfolioService(self.db, market_data)
        holdings = portfolio_service.get_holdings()

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            ["account_id", "ticker", "asset_name", "shares", "average_cost", "market_value", "unrealized_pnl", "weight"]
        )
        for h in holdings:
            writer.writerow(
                [
                    h.account_id,
                    h.ticker,
                    h.asset_name,
                    str(h.remaining_shares),
                    str(h.average_cost),
                    str(h.market_value),
                    str(h.unrealized_pnl),
                    str(h.weight) if h.weight is not None else "",
                ]
            )
        return buf.getvalue()

    def export_portfolio_snapshot_csv(self, market_data) -> str:
        portfolio_service = PortfolioService(self.db, market_data)
        summary = portfolio_service.get_summary()

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(list(summary.model_dump().keys()))
        writer.writerow([str(v) for v in summary.model_dump().values()])
        return buf.getvalue()
