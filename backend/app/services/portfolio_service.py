"""Orchestrates /api/portfolio and /api/holdings. All actual math (weighted
average cost, realized/unrealized P&L, weight) comes from app.analytics —
this service's job is fetching transactions + current prices and handing
them to the engine, then mapping the result onto API schemas. No formula
is reimplemented here.
"""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.analytics.cost_basis import calculate_positions
from app.analytics.portfolio import summarize_portfolio
from app.analytics.types import TransactionInput
from app.analytics.valuation import value_position
from app.providers.market_data_provider import AssetNotFoundError, MarketDataProvider
from app.repositories.asset_repository import AssetRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.portfolio import HoldingRead, PortfolioSummaryRead


def _to_input(txn) -> TransactionInput:
    return TransactionInput(
        id=txn.id,
        account_id=txn.account_id,
        asset_id=txn.asset_id,
        date=txn.date,
        type=txn.type,
        quantity=txn.quantity,
        price=txn.price,
        fee=txn.fee,
        tax=txn.tax,
    )


class PortfolioService:
    def __init__(self, db: Session, market_data: MarketDataProvider):
        self.db = db
        self.market_data = market_data
        self.transactions = TransactionRepository(db)
        self.assets = AssetRepository(db)

    def _valued_holdings(self, account_id: int | None = None) -> list[tuple]:
        """Returns (asset, position, valued_position, price_as_of) tuples for
        every (account_id, asset_id) pair with transaction history — open
        and closed alike. Callers filter by remaining_shares as needed."""
        all_txns = [_to_input(t) for t in self.transactions.list_all()]
        positions = calculate_positions(all_txns)

        results = []
        for (pos_account_id, asset_id), position in positions.items():
            if account_id is not None and pos_account_id != account_id:
                continue

            asset = self.assets.get(asset_id)
            latest_close = Decimal("0")
            price_as_of = None
            try:
                quote = self.market_data.get_quote(asset.ticker)
                latest_close = quote.price
                price_as_of = quote.as_of
            except AssetNotFoundError:
                pass  # no price data yet (e.g. a needs_review CSV import) -- report as zero, not a crash

            valued = value_position(position, latest_close, asset.valuation_method)
            results.append((asset, position, valued, price_as_of))

        return results

    def get_holdings(self, account_id: int | None = None) -> list[HoldingRead]:
        holdings = self._valued_holdings(account_id)
        open_positions = [h for h in holdings if h[1].remaining_shares > 0]

        total_market_value = sum((h[2].market_value for h in holdings), Decimal("0"))

        out = []
        for asset, position, valued, price_as_of in open_positions:
            weight = (valued.market_value / total_market_value) if total_market_value != 0 else None
            out.append(
                HoldingRead(
                    account_id=position.account_id,
                    asset_id=position.asset_id,
                    ticker=asset.ticker,
                    asset_name=asset.name,
                    valuation_method=asset.valuation_method,
                    remaining_shares=position.remaining_shares,
                    average_cost=position.average_cost,
                    remaining_cost_basis=position.remaining_cost,
                    latest_close=valued.latest_close,
                    price_as_of=price_as_of,
                    market_value=valued.market_value,
                    unrealized_pnl=valued.unrealized_pnl,
                    realized_pnl=position.realized_pnl,
                    total_pnl=valued.unrealized_pnl + position.realized_pnl,
                    return_pct=valued.return_pct,
                    weight=weight,
                    total_dividends_received=position.total_dividends_received,
                    total_fees_paid=position.total_fees_paid,
                    total_tax_paid=position.total_tax_paid,
                )
            )
        return out

    def get_summary(self) -> PortfolioSummaryRead:
        holdings = self._valued_holdings()
        valued_positions = [h[2] for h in holdings]
        summary = summarize_portfolio(valued_positions)
        holdings_count = sum(1 for h in holdings if h[1].remaining_shares > 0)

        return PortfolioSummaryRead(
            total_market_value=summary.total_market_value,
            remaining_cost_basis=summary.total_invested_capital,
            realized_pnl=summary.total_realized_pnl,
            unrealized_pnl=summary.total_unrealized_pnl,
            total_pnl=summary.total_unrealized_pnl + summary.total_realized_pnl,
            total_return_pct=summary.total_return_pct,
            total_dividends_received=summary.total_dividends_received,
            total_fees_paid=summary.total_fees_paid,
            total_tax_paid=summary.total_tax_paid,
            holdings_count=holdings_count,
        )
