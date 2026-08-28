from fastapi import APIRouter, Depends

from app.api.deps import get_watchlist_service
from app.schemas.watchlist import WatchlistCreate, WatchlistRead, WatchlistUpdate
from app.services.watchlist_service import WatchlistService

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


@router.get("", response_model=list[WatchlistRead])
def list_watchlist(status: str | None = None, service: WatchlistService = Depends(get_watchlist_service)):
    return service.list(status=status)


@router.post("", response_model=WatchlistRead, status_code=201)
def create_watchlist_entry(payload: WatchlistCreate, service: WatchlistService = Depends(get_watchlist_service)):
    return service.create(**payload.model_dump())


@router.put("/{watchlist_id}", response_model=WatchlistRead)
def update_watchlist_entry(
    watchlist_id: int, payload: WatchlistUpdate, service: WatchlistService = Depends(get_watchlist_service)
):
    return service.update(watchlist_id, **payload.model_dump(exclude_unset=True))


@router.delete("/{watchlist_id}", status_code=204)
def delete_watchlist_entry(watchlist_id: int, service: WatchlistService = Depends(get_watchlist_service)):
    service.delete(watchlist_id)
