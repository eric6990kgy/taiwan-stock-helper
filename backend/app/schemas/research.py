from datetime import date

from pydantic import BaseModel

from app.schemas.common import DecimalStr
from app.schemas.thesis import ThesisRead


class PricePointRead(BaseModel):
    date: date
    open: DecimalStr | None
    high: DecimalStr | None
    low: DecimalStr | None
    close: DecimalStr
    volume: int | None
    source: str


class FundamentalsRead(BaseModel):
    period: str
    revenue: DecimalStr | None
    eps: DecimalStr | None
    gross_margin: DecimalStr | None
    operating_margin: DecimalStr | None
    net_margin: DecimalStr | None
    roe: DecimalStr | None
    roa: DecimalStr | None
    debt_ratio: DecimalStr | None
    operating_cash_flow: DecimalStr | None
    free_cash_flow: DecimalStr | None
    source: str


class QuoteRead(BaseModel):
    ticker: str
    price: DecimalStr
    as_of: date
    high_52w: DecimalStr | None
    low_52w: DecimalStr | None


class ResearchPageRead(BaseModel):
    ticker: str
    name: str
    asset_type: str
    market: str | None
    sector: str | None
    industry: str | None
    is_demo_data: bool
    quote: QuoteRead
    latest_fundamentals: FundamentalsRead | None
    thesis: ThesisRead | None
