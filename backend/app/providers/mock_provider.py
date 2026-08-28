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
    FundamentalsDTO,
    MarketDataProvider,
    PricePointDTO,
    QuoteDTO,
)
from app.repositories.asset_repository import AssetRepository
from app.repositories.fundamentals_repository import FundamentalsRepository
from app.repositories.price_repository import PriceRepository


class MockMarketDataProvider(MarketDataProvider):
    def __init__(self, db: Session):
        self.assets = AssetRepository(db)
        self.prices = PriceRepository(db)
        self.fundamentals_repo = FundamentalsRepository(db)

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
            PricePointDTO(date=r.date, open=r.open, high=r.high, low=r.low, close=r.close, volume=r.volume, source=r.source)
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
