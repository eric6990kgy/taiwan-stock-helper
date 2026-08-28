from pydantic import BaseModel


class ImportSkippedRow(BaseModel):
    row: int
    reason: str


class ImportResult(BaseModel):
    imported: int
    skipped: list[ImportSkippedRow]
    needs_review_tickers: list[str]
