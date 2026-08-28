from datetime import date

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_transaction_service
from app.schemas.transaction import TransactionCreate, TransactionRead, TransactionUpdate
from app.services.transaction_service import TransactionService

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionRead])
def list_transactions(
    account_id: int | None = None,
    asset_id: int | None = None,
    type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=100, le=1000),
    offset: int = 0,
    service: TransactionService = Depends(get_transaction_service),
):
    return service.list(
        account_id=account_id, asset_id=asset_id, type=type, date_from=date_from, date_to=date_to, limit=limit, offset=offset
    )


@router.post("", response_model=TransactionRead, status_code=201)
def create_transaction(payload: TransactionCreate, service: TransactionService = Depends(get_transaction_service)):
    return service.create(**payload.model_dump())


@router.get("/{transaction_id}", response_model=TransactionRead)
def get_transaction(transaction_id: int, service: TransactionService = Depends(get_transaction_service)):
    return service.get(transaction_id)


@router.put("/{transaction_id}", response_model=TransactionRead)
def update_transaction(
    transaction_id: int, payload: TransactionUpdate, service: TransactionService = Depends(get_transaction_service)
):
    return service.update(transaction_id, **payload.model_dump(exclude_unset=True))


@router.delete("/{transaction_id}", status_code=204)
def delete_transaction(transaction_id: int, service: TransactionService = Depends(get_transaction_service)):
    service.delete(transaction_id)
