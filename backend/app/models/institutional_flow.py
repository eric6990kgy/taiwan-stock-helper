from datetime import date as date_
from datetime import datetime

from sqlalchemy import DateTime, Date, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class InstitutionalFlow(Base):
    """Daily 三大法人 (three major institutional investors) buy/sell for one
    asset, in shares. `foreign` combines FinMind's Foreign_Investor +
    Foreign_Dealer_Self categories; `dealer` combines Dealer_self +
    Dealer_Hedging -- the conventional TWSE three-way split (see
    InstitutionalFlowDTO's docstring for how the raw provider categories map
    here). Raw ingested facts only -- no derived/aggregated columns beyond
    the per-category net and the three-category total, which are cheap
    sums, not interpretations.

    One row per (asset, date) -- a market fact, not a personal holding fact.
    """

    __tablename__ = "institutional_flows"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False)
    date: Mapped[date_] = mapped_column(Date, nullable=False)

    foreign_buy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    foreign_sell: Mapped[int | None] = mapped_column(Integer, nullable=True)
    foreign_net: Mapped[int | None] = mapped_column(Integer, nullable=True)
    investment_trust_buy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    investment_trust_sell: Mapped[int | None] = mapped_column(Integer, nullable=True)
    investment_trust_net: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dealer_buy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dealer_sell: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dealer_net: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_net: Mapped[int | None] = mapped_column(Integer, nullable=True)

    source: Mapped[str] = mapped_column(String(30), nullable=False, default="MOCK")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    asset: Mapped["Asset"] = relationship(back_populates="institutional_flows")

    __table_args__ = (UniqueConstraint("asset_id", "date", name="uq_institutional_flows_asset_date"),)
