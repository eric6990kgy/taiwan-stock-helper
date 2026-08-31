from datetime import date as date_

from sqlalchemy import CheckConstraint, Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class PriceHistory(Base):
    """One row per (asset, date). `close` is the current-price source for
    TRANSACTION_BASED assets (quantity x latest close) and, for
    MANUAL_MARKET_VALUE assets, is the manually-entered *total position value*
    itself (see Asset.valuation_method). `source` records provenance
    ('MOCK', 'MANUAL', 'FINMIND', or a future provider name).

    pe_ratio/pb_ratio/dividend_yield live here (Phase 5B), not in
    `fundamentals` -- they change daily with price, same grain as this row
    (one per asset/date), whereas `fundamentals` is keyed by reporting
    period. Putting them there would have conflated two different time
    cardinalities (Phase 5 Discovery Report, Sec.7).
    """

    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False)
    date: Mapped[date_] = mapped_column(Date, nullable=False)
    open: Mapped[Numeric | None] = mapped_column(Numeric(18, 4), nullable=True)
    high: Mapped[Numeric | None] = mapped_column(Numeric(18, 4), nullable=True)
    low: Mapped[Numeric | None] = mapped_column(Numeric(18, 4), nullable=True)
    close: Mapped[Numeric] = mapped_column(Numeric(18, 4), nullable=False)
    adjusted_close: Mapped[Numeric | None] = mapped_column(Numeric(18, 4), nullable=True)
    volume: Mapped[int | None] = mapped_column(nullable=True)
    trading_value: Mapped[Numeric | None] = mapped_column(Numeric(24, 4), nullable=True)
    pe_ratio: Mapped[Numeric | None] = mapped_column(Numeric(12, 4), nullable=True)
    pb_ratio: Mapped[Numeric | None] = mapped_column(Numeric(12, 4), nullable=True)
    dividend_yield: Mapped[Numeric | None] = mapped_column(Numeric(9, 4), nullable=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="MOCK")

    asset: Mapped["Asset"] = relationship(back_populates="price_history")

    __table_args__ = (
        UniqueConstraint("asset_id", "date", name="uq_price_history_asset_date"),
        CheckConstraint("close > 0", name="ck_price_history_close_positive"),
    )
