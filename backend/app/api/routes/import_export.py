from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import PlainTextResponse

from app.api.deps import get_import_export_service, get_market_data_provider
from app.providers.market_data_provider import MarketDataProvider
from app.schemas.import_export import ImportResult
from app.services.import_export_service import ImportExportService

router = APIRouter(tags=["import-export"])


@router.post("/api/import/transactions", response_model=ImportResult)
async def import_transactions(file: UploadFile, service: ImportExportService = Depends(get_import_export_service)):
    content = (await file.read()).decode("utf-8-sig")
    return service.import_transactions(content)


@router.get("/api/export/transactions", response_class=PlainTextResponse)
def export_transactions(service: ImportExportService = Depends(get_import_export_service)):
    csv_text = service.export_transactions_csv()
    return PlainTextResponse(
        csv_text, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=transactions.csv"}
    )


@router.get("/api/export/holdings", response_class=PlainTextResponse)
def export_holdings(
    service: ImportExportService = Depends(get_import_export_service),
    market_data: MarketDataProvider = Depends(get_market_data_provider),
):
    csv_text = service.export_holdings_csv(market_data)
    return PlainTextResponse(
        csv_text, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=holdings.csv"}
    )


@router.get("/api/export/portfolio-snapshot", response_class=PlainTextResponse)
def export_portfolio_snapshot(
    service: ImportExportService = Depends(get_import_export_service),
    market_data: MarketDataProvider = Depends(get_market_data_provider),
):
    csv_text = service.export_portfolio_snapshot_csv(market_data)
    return PlainTextResponse(
        csv_text, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=portfolio-snapshot.csv"}
    )
