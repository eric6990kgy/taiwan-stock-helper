"""FastAPI dependency wiring. This is the one place that decides which
MarketDataProvider implementation is live — swapping MockMarketDataProvider
for a real one in V2 means changing get_market_data_provider() here, not
any route or service.
"""

from typing import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.providers.finmind_provider import FinMindProvider
from app.providers.market_data_provider import MarketDataProvider
from app.providers.mock_provider import MockMarketDataProvider
from app.services.account_service import AccountService
from app.services.analytics_service import AnalyticsService
from app.services.asset_service import AssetService
from app.services.import_export_service import ImportExportService
from app.services.market_data_service import MarketDataIngestionService
from app.services.portfolio_service import PortfolioService
from app.services.research_service import ResearchService
from app.services.screener_service import ScreenerService
from app.services.thesis_service import ThesisService
from app.services.transaction_service import TransactionService
from app.services.watchlist_service import WatchlistService


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_market_data_provider(db: Session = Depends(get_db)) -> MarketDataProvider:
    return MockMarketDataProvider(db)


def get_account_service(db: Session = Depends(get_db)) -> AccountService:
    return AccountService(db)


def get_asset_service(db: Session = Depends(get_db)) -> AssetService:
    return AssetService(db)


def get_transaction_service(db: Session = Depends(get_db)) -> TransactionService:
    return TransactionService(db)


def get_portfolio_service(
    db: Session = Depends(get_db), market_data: MarketDataProvider = Depends(get_market_data_provider)
) -> PortfolioService:
    return PortfolioService(db, market_data)


def get_analytics_service(portfolio_service: PortfolioService = Depends(get_portfolio_service)) -> AnalyticsService:
    return AnalyticsService(portfolio_service)


def get_watchlist_service(db: Session = Depends(get_db)) -> WatchlistService:
    return WatchlistService(db)


def get_thesis_service(db: Session = Depends(get_db)) -> ThesisService:
    return ThesisService(db)


def get_research_service(
    market_data: MarketDataProvider = Depends(get_market_data_provider),
    thesis_service: ThesisService = Depends(get_thesis_service),
) -> ResearchService:
    return ResearchService(market_data, thesis_service)


def get_screener_service(
    db: Session = Depends(get_db), market_data: MarketDataProvider = Depends(get_market_data_provider)
) -> ScreenerService:
    return ScreenerService(db, market_data)


def get_import_export_service(db: Session = Depends(get_db)) -> ImportExportService:
    return ImportExportService(db)


def get_finmind_provider() -> Generator[FinMindProvider, None, None]:
    """Distinct from get_market_data_provider() -- that one (Mock) serves
    every ordinary read in the app from the local DB. This one is used
    *only* by the manual ingestion endpoint to actually reach FinMind."""
    provider = FinMindProvider()
    try:
        yield provider
    finally:
        provider.close()


def get_market_data_service(
    db: Session = Depends(get_db), provider: FinMindProvider = Depends(get_finmind_provider)
) -> MarketDataIngestionService:
    return MarketDataIngestionService(db, provider)
