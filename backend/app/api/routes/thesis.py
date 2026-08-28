from fastapi import APIRouter, Depends

from app.api.deps import get_thesis_service
from app.schemas.thesis import ThesisRead, ThesisUpsert
from app.services.thesis_service import ThesisService

router = APIRouter(prefix="/api/thesis", tags=["thesis"])


@router.get("/{ticker}", response_model=ThesisRead)
def get_thesis(ticker: str, service: ThesisService = Depends(get_thesis_service)):
    return service.get_by_ticker(ticker)


@router.put("/{ticker}", response_model=ThesisRead)
def upsert_thesis(ticker: str, payload: ThesisUpsert, service: ThesisService = Depends(get_thesis_service)):
    return service.upsert_by_ticker(ticker, **payload.model_dump())
