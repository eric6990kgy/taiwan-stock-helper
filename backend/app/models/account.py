from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

ACCOUNT_TYPES = ("BROKERAGE", "BANK", "GLOBAL_INVEST", "CASH")


class Account(Base):
    """A place money/holdings physically sit (a brokerage, a bank, a robo-invest
    product, cash on hand) — distinct from an Asset. Positions are always derived
    per (account_id, asset_id), never globally per asset, so the same ticker held
    at two brokerages shows as two rows."""

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    account_type: Mapped[str] = mapped_column(String(20), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="TWD")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="accounts")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="account", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(f"account_type IN {ACCOUNT_TYPES}", name="ck_accounts_account_type"),
    )
