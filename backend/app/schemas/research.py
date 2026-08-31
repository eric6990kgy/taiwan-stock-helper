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


class InstitutionalFlowRead(BaseModel):
    """Buy/sell/net figures are in shares (see InstitutionalFlowDTO's
    docstring for how FinMind's five raw categories map into this
    three-way foreign/investment_trust/dealer split)."""

    date: date
    foreign_buy: int | None
    foreign_sell: int | None
    foreign_net: int | None
    investment_trust_buy: int | None
    investment_trust_sell: int | None
    investment_trust_net: int | None
    dealer_buy: int | None
    dealer_sell: int | None
    dealer_net: int | None
    total_net: int | None
    source: str


class MarginTradingRead(BaseModel):
    """All fields are in 張 (board lots, 1 lot = 1,000 shares) -- see
    MarginTradingDTO's docstring."""

    date: date
    margin_buy: int | None
    margin_sell: int | None
    margin_cash_repayment: int | None
    margin_balance: int | None
    short_sale_buy: int | None
    short_sale_sell: int | None
    short_sale_cash_repayment: int | None
    short_sale_balance: int | None
    source: str


class MonthlyRevenueRead(BaseModel):
    """yoy_growth/mom_growth are computed on read from the persisted raw
    revenue facts (never stored) -- None whenever the comparison period is
    missing or would divide by zero, never a fabricated 0%."""

    revenue_year: int
    revenue_month: int
    revenue: DecimalStr
    yoy_growth: DecimalStr | None
    mom_growth: DecimalStr | None
    announcement_date: date | None
    source: str


class TechnicalIndicatorValues(BaseModel):
    sma_5: DecimalStr | None
    sma_20: DecimalStr | None
    ema_20: DecimalStr | None
    rsi_14: DecimalStr | None
    macd: DecimalStr | None
    macd_signal: DecimalStr | None
    macd_histogram: DecimalStr | None
    bollinger_upper: DecimalStr | None
    bollinger_middle: DecimalStr | None
    bollinger_lower: DecimalStr | None
    kd_k: DecimalStr | None
    kd_d: DecimalStr | None


class TechnicalIndicatorsRead(BaseModel):
    ticker: str
    as_of: date | None
    indicators: TechnicalIndicatorValues
    source: str = "CALCULATED"
