from datetime import date as date_

from sqlalchemy import CheckConstraint, Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class PriceHistory(Base):
    """One row per (asset, date). `close` is the current-price source for
    TRANSACTION_BASED assets (quantity x latest close) and, for
    MANUAL_MARKET_VALUE assets, is the manually-entered *total position value*
    itself (see Asset.valuation_method). `source` records provenance
    ('MOCK', 'MANUAL', or a real provider name in future versions)."""

    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False)
    date: Mapped[date_] = mapped_column(Date, nullable=False)
    open: Mapped[Numeric | None] = mapped_column(Numeric(18, 4), nullable=True)
    high: Mapped[Numeric | None] = mapped_column(Numeric(18, 4), nullable=True)
    low: Mapped[Numeric | None] = mapped_column(Numeric(18, 4), nullable=True)
    close: Mapped[Numeric] = mapped_column(Numeric(18, 4), nullable=False)
    volume: Mapped[int | None] = mapped_column(nullable=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="MOCK")

    asset: Mapped["Asset"] = relationship(back_populates="price_history")

    __table_args__ = (
        UniqueConstraint("asset_id", "date", name="uq_price_history_asset_date"),
        CheckConstraint("close > 0", name="ck_price_history_close_positive"),
    )
