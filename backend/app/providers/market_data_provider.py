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


class AssetNotFoundError(Exception):
    """Raised by a provider when the ticker doesn't exist in its data
    source. Kept local to this package (rather than importing
    app.services.exceptions) so providers stay a standalone layer with no
    upward dependency on services."""

    def __init__(self, ticker: str):
        self.ticker = ticker
        super().__init__(f"Unknown ticker: {ticker!r}")


class MarketDataProvider(ABC):
    @abstractmethod
    def get_quote(self, ticker: str) -> QuoteDTO: ...

    @abstractmethod
    def get_historical_prices(self, ticker: str, start: date | None = None, end: date | None = None) -> list[PricePointDTO]: ...

    @abstractmethod
    def get_fundamentals(self, ticker: str) -> list[FundamentalsDTO]: ...

    @abstractmethod
    def get_company_info(self, ticker: str) -> CompanyInfoDTO: ...
