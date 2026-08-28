from fastapi import APIRouter, Depends

from app.api.deps import get_account_service
from app.schemas.account import AccountCreate, AccountRead, AccountUpdate
from app.services.account_service import AccountService

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountRead])
def list_accounts(service: AccountService = Depends(get_account_service)):
    return service.list()


@router.post("", response_model=AccountRead, status_code=201)
def create_account(payload: AccountCreate, service: AccountService = Depends(get_account_service)):
    return service.create(**payload.model_dump())


@router.get("/{account_id}", response_model=AccountRead)
def get_account(account_id: int, service: AccountService = Depends(get_account_service)):
    return service.get(account_id)


@router.put("/{account_id}", response_model=AccountRead)
def update_account(account_id: int, payload: AccountUpdate, service: AccountService = Depends(get_account_service)):
    return service.update(account_id, **payload.model_dump(exclude_unset=True))


@router.delete("/{account_id}", status_code=204)
def delete_account(account_id: int, service: AccountService = Depends(get_account_service)):
    service.delete(account_id)
