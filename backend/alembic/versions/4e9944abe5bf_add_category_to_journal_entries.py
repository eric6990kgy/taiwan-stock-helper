"""add_category_to_journal_entries

Revision ID: 4e9944abe5bf
Revises: 505c5e07183e
Create Date: 2026-09-17 11:50:00.000982

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e9944abe5bf'
down_revision: Union[str, Sequence[str], None] = '505c5e07183e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # SQLite can't ALTER a table to add a CHECK constraint directly --
    # batch mode does the copy-and-move dance for us (first time this repo
    # has retrofitted a CheckConstraint onto an existing table; every prior
    # one was defined at CREATE TABLE time).
    with op.batch_alter_table("journal_entries") as batch_op:
        # server_default so this stays safe to run against a non-empty
        # table (the table is empty today, but this shouldn't assume that
        # forever).
        batch_op.add_column(sa.Column("category", sa.String(length=20), nullable=False, server_default="OBSERVATION"))
        batch_op.create_check_constraint(
            "ck_journal_entries_category", "category IN ('BUY_REASON', 'SELL_REASON', 'OBSERVATION', 'REVIEW', 'OTHER')"
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("journal_entries") as batch_op:
        batch_op.drop_constraint("ck_journal_entries_category", type_="check")
        batch_op.drop_column("category")
