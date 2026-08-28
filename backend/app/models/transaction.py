from datetime import date as date_, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

TRANSACTION_TYPES = ("BUY", "SELL", "DIVIDEND", "FEE", "CASH_DEPOSIT", "CASH_WITHDRAWAL")


class Transaction(Base):
    """The source of truth (Principle 2). Holdings/positions/P&L are always
    *derived* from these rows by the Phase 2 calculation engine — never stored
    directly.

    Uniform arithmetic shape across all types: gross_amount = quantity x price.
    - BUY:  cost added   = quantity x price + fee
    - SELL: proceeds     = quantity x price - fee - tax
    - DIVIDEND: quantity x price = cash received (does not touch cost basis)
    - CASH_DEPOSIT/WITHDRAWAL: quantity = cash amount, price fixed at 1
    - For a MANUAL_MARKET_VALUE asset (see Asset), BUY quantity = amount
      contributed, price = 1, so invested-capital math stays correct even
      though market value is later read from a manual valuation instead of
      quantity x price.
    """

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False)
    date: Mapped[date_] = mapped_column(Date, nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[Numeric] = mapped_column(Numeric(18, 4), nullable=False)
    price: Mapped[Numeric] = mapped_column(Numeric(18, 4), nullable=False)
    fee: Mapped[Numeric] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    tax: Mapped[Numeric] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="TWD")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    account: Mapped["Account"] = relationship(back_populates="transactions")
    asset: Mapped["Asset"] = relationship(back_populates="transactions")

    __table_args__ = (
        CheckConstraint(f"type IN {TRANSACTION_TYPES}", name="ck_transactions_type"),
        CheckConstraint("quantity > 0", name="ck_transactions_quantity_positive"),
        CheckConstraint("price > 0", name="ck_transactions_price_positive"),
        CheckConstraint("fee >= 0", name="ck_transactions_fee_nonnegative"),
        CheckConstraint("tax >= 0", name="ck_transactions_tax_nonnegative"),
        Index("ix_transactions_account_asset", "account_id", "asset_id"),
        Index("ix_transactions_date", "date"),
    )
