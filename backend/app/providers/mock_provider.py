"""V1's only MarketDataProvider implementation. "Mock" means it serves the
locally seeded/manually-entered data in our own DB (price_history,
fundamentals, assets) rather than calling any real external API — there is
no live market data in V1 (architecture decision A5). Swapping this for
FugleProvider/YahooFinanceProvider later touches only the dependency wiring
in app/api/deps.py, nothing that calls MarketDataProvider.
"""

from datetime import date

from sqlalchemy.orm import Session

from app.providers.market_data_provider import (
    AssetNotFoundError,
    CompanyInfoDTO,
    DividendDTO,
    FundamentalsDTO,
    InstitutionalFlowDTO,
    MarginTradingDTO,
    MarketDataProvider,
    MonthlyRevenueDTO,
    PricePointDTO,
    QuoteDTO,
    ValuationDTO,
)
from app.repositories.asset_repository import AssetRepository
from app.repositories.dividend_repository import DividendRepository
from app.repositories.fundamentals_repository import FundamentalsRepository
from app.repositories.institutional_flow_repository import InstitutionalFlowRepository
from app.repositories.margin_trading_repository import MarginTradingRepository
from app.repositories.monthly_revenue_repository import MonthlyRevenueRepository
from app.repositories.price_repository import PriceRepository


class MockMarketDataProvider(MarketDataProvider):
    """Despite the name, this is the provider that serves every *read* in
    the app (Dashboard, Research, Screener, ...) straight from the local DB
    -- whether that DB holds seeded MOCK rows or real FINMIND-sourced rows
    ingested via MarketDataIngestionService makes no difference to it. Only
    the (separate) ingestion path talks to FinMindProvider directly; this
    class never does."""

    def __init__(self, db: Session):
        self.assets = AssetRepository(db)
        self.prices = PriceRepository(db)
        self.fundamentals_repo = FundamentalsRepository(db)
        self.dividends_repo = DividendRepository(db)
        self.institutional_flows_repo = InstitutionalFlowRepository(db)
        self.margin_trading_repo = MarginTradingRepository(db)
        self.monthly_revenue_repo = MonthlyRevenueRepository(db)

    def _get_asset(self, ticker: str):
        asset = self.assets.get_by_ticker(ticker)
        if asset is None:
            raise AssetNotFoundError(ticker)
        return asset

    def get_quote(self, ticker: str) -> QuoteDTO:
        asset = self._get_asset(ticker)
        latest = self.prices.latest(asset.id)
        if latest is None:
            raise AssetNotFoundError(ticker)

        history = self.prices.range(asset.id)
        one_year_ago = date(latest.date.year - 1, latest.date.month, latest.date.day)
        recent = [p for p in history if p.date >= one_year_ago] or history
        highs = [p.high or p.close for p in recent]
        lows = [p.low or p.close for p in recent]

        return QuoteDTO(
            ticker=ticker,
            price=latest.close,
            as_of=latest.date,
            high_52w=max(highs) if highs else None,
            low_52w=min(lows) if lows else None,
        )

    def get_historical_prices(self, ticker: str, start: date | None = None, end: date | None = None) -> list[PricePointDTO]:
        asset = self._get_asset(ticker)
        rows = self.prices.range(asset.id, start, end)
        return [
            PricePointDTO(
                date=r.date,
                open=r.open,
                high=r.high,
                low=r.low,
                close=r.close,
                volume=r.volume,
                source=r.source,
                adjusted_close=r.adjusted_close,
                trading_value=r.trading_value,
            )
            for r in rows
        ]

    def get_fundamentals(self, ticker: str) -> list[FundamentalsDTO]:
        asset = self._get_asset(ticker)
        rows = self.fundamentals_repo.list_by_asset(asset.id)
        return [
            FundamentalsDTO(
                period=r.period,
                revenue=r.revenue,
                eps=r.eps,
                gross_margin=r.gross_margin,
                operating_margin=r.operating_margin,
                net_margin=r.net_margin,
                roe=r.roe,
                roa=r.roa,
                debt_ratio=r.debt_ratio,
                operating_cash_flow=r.operating_cash_flow,
                free_cash_flow=r.free_cash_flow,
                source=r.source,
            )
            for r in rows
        ]

    def get_company_info(self, ticker: str) -> CompanyInfoDTO:
        asset = self._get_asset(ticker)
        return CompanyInfoDTO(
            ticker=asset.ticker,
            name=asset.name,
            asset_type=asset.asset_type,
            market=asset.market,
            sector=asset.sector,
            industry=asset.industry,
            is_demo_data=asset.is_demo_data,
        )

    def get_dividends(self, ticker: str, start: date | None = None, end: date | None = None) -> list[DividendDTO]:
        asset = self._get_asset(ticker)
        rows = self.dividends_repo.range(asset.id, start, end)
        return [
            DividendDTO(
                ex_dividend_date=r.ex_dividend_date,
                payment_date=r.payment_date,
                cash_dividend=r.cash_dividend,
                stock_dividend=r.stock_dividend,
                source=r.source,
            )
            for r in rows
        ]

    def get_valuation(self, ticker: str, on_date: date | None = None) -> ValuationDTO:
        asset = self._get_asset(ticker)
        row = self.prices.get_by_asset_and_date(asset.id, on_date) if on_date else self.prices.latest(asset.id)
        if row is None:
            raise AssetNotFoundError(ticker)

        market_cap = (asset.shares_outstanding * row.close) if asset.shares_outstanding is not None else None
        return ValuationDTO(
            date=row.date,
            pe_ratio=row.pe_ratio,
            pb_ratio=row.pb_ratio,
            dividend_yield=row.dividend_yield,
            market_cap=market_cap,
            shares_outstanding=asset.shares_outstanding,
            source=row.source,
        )

    def get_institutional_flows(
        self, ticker: str, start: date | None = None, end: date | None = None
    ) -> list[InstitutionalFlowDTO]:
        asset = self._get_asset(ticker)
        rows = self.institutional_flows_repo.range(asset.id, start, end)
        return [
            InstitutionalFlowDTO(
                date=r.date,
                foreign_buy=r.foreign_buy,
                foreign_sell=r.foreign_sell,
                foreign_net=r.foreign_net,
                investment_trust_buy=r.investment_trust_buy,
                investment_trust_sell=r.investment_trust_sell,
                investment_trust_net=r.investment_trust_net,
                dealer_buy=r.dealer_buy,
                dealer_sell=r.dealer_sell,
                dealer_net=r.dealer_net,
                total_net=r.total_net,
                source=r.source,
            )
            for r in rows
        ]

    def get_margin_trading(
        self, ticker: str, start: date | None = None, end: date | None = None
    ) -> list[MarginTradingDTO]:
        asset = self._get_asset(ticker)
        rows = self.margin_trading_repo.range(asset.id, start, end)
        return [
            MarginTradingDTO(
                date=r.date,
                margin_buy=r.margin_buy,
                margin_sell=r.margin_sell,
                margin_cash_repayment=r.margin_cash_repayment,
                margin_balance=r.margin_balance,
                short_sale_buy=r.short_sale_buy,
                short_sale_sell=r.short_sale_sell,
                short_sale_cash_repayment=r.short_sale_cash_repayment,
                short_sale_balance=r.short_sale_balance,
                source=r.source,
            )
            for r in rows
        ]

    def get_monthly_revenue(self, ticker: str) -> list[MonthlyRevenueDTO]:
        asset = self._get_asset(ticker)
        rows = self.monthly_revenue_repo.list_by_asset(asset.id)
        return [
            MonthlyRevenueDTO(
                revenue_year=r.revenue_year,
                revenue_month=r.revenue_month,
                revenue=r.revenue,
                announcement_date=r.announcement_date,
                source=r.source,
            )
            for r in rows
        ]
