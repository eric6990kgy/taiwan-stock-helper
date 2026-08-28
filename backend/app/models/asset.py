from sqlalchemy import Boolean, CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

ASSET_TYPES = ("STOCK", "ETF", "CASH", "FUND")
VALUATION_METHODS = ("TRANSACTION_BASED", "MANUAL_MARKET_VALUE")


class Asset(Base):
    """A tradeable/trackable thing: a TW stock, the Global ETF robo-product
    (asset_type=FUND), or a cash placeholder.

    valuation_method drives how market value is computed (see analytics layer,
    Phase 2):
      - TRANSACTION_BASED (default): market_value = quantity x latest price_history.close
      - MANUAL_MARKET_VALUE: deposits are recorded as BUY transactions with
        quantity=amount, price=1 (so invested-capital math stays correct), and
        market_value = the latest price_history.close taken directly as the
        position's total value, ignoring quantity. Used for the Global ETF
        fund where per-unit price isn't a number the user tracks.
    """

    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(20), nullable=False)
    market: Mapped[str | None] = mapped_column(String(30), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="TWD")
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    valuation_method: Mapped[str] = mapped_column(String(30), nullable=False, default="TRANSACTION_BASED")
    is_demo_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Set True when a CSV import auto-creates this asset from an unrecognized
    # ticker (A11), so a placeholder row doesn't silently pass as researched.
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="asset", cascade="all, delete-orphan")
    watchlist_entry: Mapped["Watchlist"] = relationship(back_populates="asset", uselist=False, cascade="all, delete-orphan")
    thesis: Mapped["InvestmentThesis"] = relationship(back_populates="asset", uselist=False, cascade="all, delete-orphan")
    price_history: Mapped[list["PriceHistory"]] = relationship(back_populates="asset", cascade="all, delete-orphan")
    fundamentals: Mapped[list["Fundamentals"]] = relationship(back_populates="asset", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(f"asset_type IN {ASSET_TYPES}", name="ck_assets_asset_type"),
        CheckConstraint(f"valuation_method IN {VALUATION_METHODS}", name="ck_assets_valuation_method"),
    )
