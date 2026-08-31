from datetime import date as date_
from datetime import datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Dividend(Base):
    """Market-wide dividend calendar data for an asset -- e.g. "2330 goes
    ex-dividend on 2026-06-13, NT$3.50 cash". This is deliberately separate
    from a user's own DIVIDEND-type Transaction row: that's a personal fact
    (money the user actually received into their account), this is a market
    fact (what the company announced/paid), per the Phase 5 Discovery
    Report's explicit personal-holdings-vs-market-data separation (Sec.13).

    One row per (asset, ex_dividend_date) -- a company can distribute more
    than once a year (TSMC pays quarterly), so ex_dividend_date, not asset_id
    alone, is the natural key.
    """

    __tablename__ = "dividends"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False)
    ex_dividend_date: Mapped[date_] = mapped_column(Date, nullable=False)
    payment_date: Mapped[date_ | None] = mapped_column(Date, nullable=True)
    cash_dividend: Mapped[Numeric | None] = mapped_column(Numeric(18, 4), nullable=True)
    stock_dividend: Mapped[Numeric | None] = mapped_column(Numeric(18, 4), nullable=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="MOCK")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    asset: Mapped["Asset"] = relationship(back_populates="dividends")

    __table_args__ = (
        UniqueConstraint("asset_id", "ex_dividend_date", name="uq_dividends_asset_exdate"),
        CheckConstraint(
            "cash_dividend IS NOT NULL OR stock_dividend IS NOT NULL", name="ck_dividends_has_a_dividend"
        ),
    )
