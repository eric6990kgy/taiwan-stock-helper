from datetime import date as date_, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

JOURNAL_CATEGORIES = ("BUY_REASON", "SELL_REASON", "OBSERVATION", "REVIEW", "OTHER")


class JournalEntry(Base):
    """A dated, freeform note (投資日誌, Phase 10) -- append-only history,
    unlike InvestmentThesis's one-row-per-asset upsert ("what I currently
    believe" vs. "what I observed/decided on this date"). Both `asset_id`
    and `recommendation_id` are optional: a general note needs neither, one
    about a specific stock sets asset_id, one written in response to a
    specific recommendation sets both. `category` is a fixed, filterable
    tag (requested so entries stay manageable as the log grows) -- not
    free text, so "what did I buy X for" can actually be filtered later,
    not just grepped."""

    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_date: Mapped[date_] = mapped_column(Date, nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False, default="OBSERVATION")
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id"), nullable=True)
    recommendation_id: Mapped[int | None] = mapped_column(ForeignKey("recommendations.id"), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (CheckConstraint(f"category IN {JOURNAL_CATEGORIES}", name="ck_journal_entries_category"),)
