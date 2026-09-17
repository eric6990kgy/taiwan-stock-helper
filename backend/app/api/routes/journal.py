from datetime import date

from fastapi import APIRouter, Depends

from app.api.deps import get_journal_service
from app.schemas.journal import JournalEntryCreate, JournalEntryRead, JournalEntryUpdate
from app.services.journal_service import JournalService

router = APIRouter(prefix="/api/journal", tags=["journal"])


@router.get("", response_model=list[JournalEntryRead])
def list_journal_entries(
    asset_id: int | None = None,
    category: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    service: JournalService = Depends(get_journal_service),
):
    return service.list(asset_id=asset_id, category=category, date_from=date_from, date_to=date_to)


@router.post("", response_model=JournalEntryRead, status_code=201)
def create_journal_entry(payload: JournalEntryCreate, service: JournalService = Depends(get_journal_service)):
    return service.create(**payload.model_dump())


@router.put("/{entry_id}", response_model=JournalEntryRead)
def update_journal_entry(
    entry_id: int, payload: JournalEntryUpdate, service: JournalService = Depends(get_journal_service)
):
    return service.update(entry_id, **payload.model_dump(exclude_unset=True))


@router.delete("/{entry_id}", status_code=204)
def delete_journal_entry(entry_id: int, service: JournalService = Depends(get_journal_service)):
    service.delete(entry_id)
