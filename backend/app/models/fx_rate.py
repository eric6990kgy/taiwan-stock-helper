from datetime import date as date_

from sqlalchemy import Date, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class FxRate(Base):
    """Reserved for V2+ multi-currency support (decision A3). Unused in V1 —
    all V1 transactions are TWD-only, enforced at the service layer rather
    than by a DB constraint so this table can be activated without a
    migration when FX support is built."""

    __tablename__ = "fx_rates"

    id: Mapped[int] = mapped_column(primary_key=True)
    base_currency: Mapped[str] = mapped_column(String(10), nullable=False)
    quote_currency: Mapped[str] = mapped_column(String(10), nullable=False)
    date: Mapped[date_] = mapped_column(Date, nullable=False)
    rate: Mapped[Numeric] = mapped_column(Numeric(18, 6), nullable=False)

    __table_args__ = (
        UniqueConstraint("base_currency", "quote_currency", "date", name="uq_fx_rates_pair_date"),
    )
