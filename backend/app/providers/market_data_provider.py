"""The market data abstraction (architecture Sec.31). Nothing in the service
layer or routes should know whether prices/fundamentals/company info come
from our own seeded DB (V1's MockMarketDataProvider) or a real vendor
(TaiwanMarketDataProvider / FugleProvider / YahooFinanceProvider, future) —
they only depend on this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class QuoteDTO:
    ticker: str
    price: Decimal
    as_of: date
    high_52w: Decimal | None = None
    low_52w: Decimal | None = None


@dataclass(frozen=True)
class PricePointDTO:
    date: date
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None
    close: Decimal
    volume: int | None
    source: str
    adjusted_close: Decimal | None = None
    trading_value: Decimal | None = None


@dataclass(frozen=True)
class FundamentalsDTO:
    period: str
    revenue: Decimal | None
    eps: Decimal | None
    gross_margin: Decimal | None
    operating_margin: Decimal | None
    net_margin: Decimal | None
    roe: Decimal | None
    roa: Decimal | None
    debt_ratio: Decimal | None
    operating_cash_flow: Decimal | None
    free_cash_flow: Decimal | None
    source: str


@dataclass(frozen=True)
class CompanyInfoDTO:
    ticker: str
    name: str
    asset_type: str
    market: str | None
    sector: str | None
    industry: str | None
    is_demo_data: bool


@dataclass(frozen=True)
class DividendDTO:
    """Market-wide dividend calendar data (Phase 5B) -- not the user's own
    dividend receipt (that's a Transaction row); see app/models/dividend.py.
    """

    ex_dividend_date: date
    payment_date: date | None
    cash_dividend: Decimal | None
    stock_dividend: Decimal | None
    source: str


@dataclass(frozen=True)
class ValuationDTO:
    """Point-in-time valuation ratios (Phase 5B) -- same grain as a single
    price_history row (one per asset/date), never the `fundamentals` table's
    period grain. market_cap/shares_outstanding are commonly unavailable on
    a provider's free tier (confirmed true for FinMind) and are therefore
    optional here, not a broken contract when null."""

    date: date
    pe_ratio: Decimal | None
    pb_ratio: Decimal | None
    dividend_yield: Decimal | None
    market_cap: Decimal | None
    shares_outstanding: Decimal | None
    source: str


@dataclass(frozen=True)
class InstitutionalFlowDTO:
    """Daily 三大法人 (three major institutional investors) buy/sell for one
    asset, in shares. `foreign` combines FinMind's Foreign_Investor +
    Foreign_Dealer_Self categories, and `dealer` combines Dealer_self +
    Dealer_Hedging -- the conventional TWSE three-way split (Sec.7 of the
    Phase 6 spec), not a 1:1 mirror of FinMind's five raw categories."""

    date: date
    foreign_buy: int | None
    foreign_sell: int | None
    foreign_net: int | None
    investment_trust_buy: int | None
    investment_trust_sell: int | None
    investment_trust_net: int | None
    dealer_buy: int | None
    dealer_sell: int | None
    dealer_net: int | None
    total_net: int | None
    source: str


@dataclass(frozen=True)
class MarginTradingDTO:
    """Daily 融資融券 (margin purchase / short sale) for one asset. All
    fields are in 張 (board lots, 1 lot = 1,000 shares) -- confirmed against
    FinMind's live API by cross-checking TaiwanStockMarginPurchaseShortSale's
    MarginPurchaseTodayBalance for 2330 against TWSE's own published 融資餘額
    for the same date (same order of magnitude, ~27-28k), not shares (which
    would be three orders of magnitude larger for a stock this size)."""

    date: date
    margin_buy: int | None
    margin_sell: int | None
    margin_cash_repayment: int | None
    margin_balance: int | None
    short_sale_buy: int | None
    short_sale_sell: int | None
    short_sale_cash_repayment: int | None
    short_sale_balance: int | None
    source: str


@dataclass(frozen=True)
class MonthlyRevenueDTO:
    """One row per (asset, revenue_year, revenue_month) -- keyed by the
    *covered* month, not FinMind's `date` field (which is the first of the
    month the figure was *announced* in, e.g. date=2026-08-01 for
    revenue_month=7/revenue_year=2026's July revenue, announced by Taiwan's
    regulatory 10th-of-the-month deadline). `announcement_date` keeps that
    raw `date` value for reference."""

    revenue_year: int
    revenue_month: int
    revenue: Decimal
    announcement_date: date | None
    source: str


class AssetNotFoundError(Exception):
    """Raised by a provider when the ticker doesn't exist in its data
    source. Kept local to this package (rather than importing
    app.services.exceptions) so providers stay a standalone layer with no
    upward dependency on services."""

    def __init__(self, ticker: str):
        self.ticker = ticker
        super().__init__(f"Unknown ticker: {ticker!r}")


class ProviderError(Exception):
    """A real market-data provider (e.g. FinMind) failed in a way that isn't
    "ticker not found" -- network failure, unexpected response shape, or an
    API-level error message. Kept distinct from AssetNotFoundError so
    ingestion can tell "this ticker doesn't exist" apart from "the provider
    is currently broken/unreachable" (Phase 5B Sec.6: provider errors must
    be surfaced clearly, never silently swallowed)."""


class RateLimitError(ProviderError):
    """The provider's request quota was exceeded. A distinct type from a
    generic ProviderError so the ingestion service can stop the whole batch
    early (retrying immediately would just fail again) instead of burning
    through the remaining tickers one failure at a time."""


class MarketDataProvider(ABC):
    @abstractmethod
    def get_quote(self, ticker: str) -> QuoteDTO: ...

    @abstractmethod
    def get_historical_prices(self, ticker: str, start: date | None = None, end: date | None = None) -> list[PricePointDTO]: ...

    @abstractmethod
    def get_fundamentals(self, ticker: str) -> list[FundamentalsDTO]: ...

    @abstractmethod
    def get_company_info(self, ticker: str) -> CompanyInfoDTO: ...

    @abstractmethod
    def get_dividends(self, ticker: str, start: date | None = None, end: date | None = None) -> list[DividendDTO]: ...

    @abstractmethod
    def get_valuation(self, ticker: str, on_date: date | None = None) -> ValuationDTO: ...

    @abstractmethod
    def get_institutional_flows(
        self, ticker: str, start: date | None = None, end: date | None = None
    ) -> list[InstitutionalFlowDTO]: ...

    @abstractmethod
    def get_margin_trading(
        self, ticker: str, start: date | None = None, end: date | None = None
    ) -> list[MarginTradingDTO]: ...

    @abstractmethod
    def get_monthly_revenue(self, ticker: str) -> list[MonthlyRevenueDTO]: ...
