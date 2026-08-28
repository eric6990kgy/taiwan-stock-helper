"""Response shapes for /api/portfolio and /api/holdings.

Naming note (explicit user instruction, Phase 3 kickoff): the calculation
engine's `PortfolioSummary.total_invested_capital` is the *remaining* cost
basis of currently-held positions, not lifetime capital ever contributed.
It is exposed here as `remaining_cost_basis` — never as `invested_capital`
— to avoid implying a "money ever put in" semantic the engine doesn't
compute. `lifetime_contributions` is intentionally not a field on any
schema in this phase; its calculation isn't defined yet.
"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.common import DecimalStr


class HoldingRead(BaseModel):
    account_id: int
    asset_id: int
    ticker: str
    asset_name: str
    valuation_method: str
    remaining_shares: DecimalStr
    average_cost: DecimalStr
    remaining_cost_basis: DecimalStr
    latest_close: DecimalStr
    price_as_of: date | None
    market_value: DecimalStr
    unrealized_pnl: DecimalStr
    realized_pnl: DecimalStr
    total_pnl: DecimalStr
    return_pct: DecimalStr | None
    weight: DecimalStr | None
    total_dividends_received: DecimalStr
    total_fees_paid: DecimalStr
    total_tax_paid: DecimalStr


class PortfolioSummaryRead(BaseModel):
    total_market_value: DecimalStr
    remaining_cost_basis: DecimalStr
    realized_pnl: DecimalStr
    unrealized_pnl: DecimalStr
    total_pnl: DecimalStr
    total_return_pct: DecimalStr | None
    total_dividends_received: DecimalStr
    total_fees_paid: DecimalStr
    total_tax_paid: DecimalStr
    holdings_count: int
