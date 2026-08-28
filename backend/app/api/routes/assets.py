from fastapi import APIRouter, Depends

from app.api.deps import get_asset_service
from app.schemas.asset import AssetCreate, AssetRead, AssetUpdate
from app.services.asset_service import AssetService

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("", response_model=list[AssetRead])
def list_assets(service: AssetService = Depends(get_asset_service)):
    return service.list()


@router.post("", response_model=AssetRead, status_code=201)
def create_asset(payload: AssetCreate, service: AssetService = Depends(get_asset_service)):
    return service.create(**payload.model_dump())


@router.get("/{ticker}", response_model=AssetRead)
def get_asset_by_ticker(ticker: str, service: AssetService = Depends(get_asset_service)):
    return service.get_by_ticker(ticker)


@router.put("/{asset_id}", response_model=AssetRead)
def update_asset(asset_id: int, payload: AssetUpdate, service: AssetService = Depends(get_asset_service)):
    return service.update(asset_id, **payload.model_dump(exclude_unset=True))


@router.delete("/{asset_id}", status_code=204)
def delete_asset(asset_id: int, service: AssetService = Depends(get_asset_service)):
    service.delete(asset_id)
