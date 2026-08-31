from datetime import date as date_
from datetime import datetime

from sqlalchemy import DateTime, Date, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class MarginTrading(Base):
    """Daily 融資融券 (margin purchase / short sale) for one asset. All
    balance/volume fields are in 張 (board lots, 1 lot = 1,000 shares) --
    see MarginTradingDTO's docstring for how that unit was confirmed against
    FinMind's live API. Raw ingested facts only, one row per (asset, date).
    """

    __tablename__ = "margin_trading"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False)
    date: Mapped[date_] = mapped_column(Date, nullable=False)

    margin_buy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    margin_sell: Mapped[int | None] = mapped_column(Integer, nullable=True)
    margin_cash_repayment: Mapped[int | None] = mapped_column(Integer, nullable=True)
    margin_balance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    short_sale_buy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    short_sale_sell: Mapped[int | None] = mapped_column(Integer, nullable=True)
    short_sale_cash_repayment: Mapped[int | None] = mapped_column(Integer, nullable=True)
    short_sale_balance: Mapped[int | None] = mapped_column(Integer, nullable=True)

    source: Mapped[str] = mapped_column(String(30), nullable=False, default="MOCK")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    asset: Mapped["Asset"] = relationship(back_populates="margin_trading_rows")

    __table_args__ = (UniqueConstraint("asset_id", "date", name="uq_margin_trading_asset_date"),)
