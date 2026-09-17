from fastapi import APIRouter, Depends

from app.api.deps import get_asset_service, get_market_data_service
from app.schemas.asset import AssetCreate, AssetRead, AssetUpdate, QuickCreateAsset, TickerLookupRead
from app.services.asset_service import AssetService
from app.services.market_data_service import MarketDataIngestionService

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("", response_model=list[AssetRead])
def list_assets(service: AssetService = Depends(get_asset_service)):
    return service.list()


@router.post("", response_model=AssetRead, status_code=201)
def create_asset(payload: AssetCreate, service: AssetService = Depends(get_asset_service)):
    return service.create(**payload.model_dump())


@router.get("/lookup/{ticker}", response_model=TickerLookupRead)
def lookup_ticker(ticker: str, ingestion: MarketDataIngestionService = Depends(get_market_data_service)):
    """Phase 11: a real FinMind company-info lookup (not the local-DB Mock
    provider, which only works for tickers already tracked) -- lets the
    frontend preview the real name/market for a brand-new ticker before the
    user commits to adding it. Raises AssetNotFoundError -> 404 (existing
    handler) for an unknown ticker."""
    info = ingestion.provider.get_company_info(ticker)
    return TickerLookupRead(
        ticker=info.ticker, name=info.name, asset_type=info.asset_type, market=info.market,
        sector=info.sector, industry=info.industry,
    )


@router.post("/quick-create", response_model=AssetRead, status_code=201)
def quick_create_asset(
    payload: QuickCreateAsset,
    asset_service: AssetService = Depends(get_asset_service),
    ingestion: MarketDataIngestionService = Depends(get_market_data_service),
):
    """Phase 11: the "just type the ticker" flow -- looks up the real
    name/market/sector from FinMind, creates the asset, then immediately
    backfills its price/fundamentals/etc. (best-effort, same as clicking
    "Update Market Data") so it never sits at a misleading $0 market value
    until the next scheduled update."""
    info = ingestion.provider.get_company_info(payload.ticker)
    asset = asset_service.create(
        ticker=info.ticker, name=info.name, asset_type=info.asset_type,
        market=info.market, sector=info.sector, industry=info.industry, currency="TWD",
    )
    ingestion.update_all(tickers=[payload.ticker])
    return asset


@router.get("/{ticker}", response_model=AssetRead)
def get_asset_by_ticker(ticker: str, service: AssetService = Depends(get_asset_service)):
    return service.get_by_ticker(ticker)


@router.put("/{asset_id}", response_model=AssetRead)
def update_asset(asset_id: int, payload: AssetUpdate, service: AssetService = Depends(get_asset_service)):
    return service.update(asset_id, **payload.model_dump(exclude_unset=True))


@router.delete("/{asset_id}", status_code=204)
def delete_asset(asset_id: int, service: AssetService = Depends(get_asset_service)):
    service.delete(asset_id)
