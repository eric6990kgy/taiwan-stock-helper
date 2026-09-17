"""phase_12_structured_agent_analysis_fields

Revision ID: 40ca7918d59f
Revises: a3ea98c9cdec
Create Date: 2026-09-17 15:06:18.880115

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '40ca7918d59f'
down_revision: Union[str, Sequence[str], None] = 'a3ea98c9cdec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # rationale (one free-text paragraph) -> details (a handful of short,
    # role-specific labeled fields) -- the field set differs per role, so
    # this is JSON, not new fixed columns. Existing rows predate this
    # shape and are cheap to regenerate (one Gemini call each), so this
    # drops rationale outright rather than trying to migrate its content.
    with op.batch_alter_table("agent_analyses") as batch_op:
        batch_op.drop_column("rationale")
        batch_op.add_column(sa.Column("details", sa.JSON(), nullable=False, server_default="{}"))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("agent_analyses") as batch_op:
        batch_op.drop_column("details")
        batch_op.add_column(sa.Column("rationale", sa.Text(), nullable=False, server_default=""))
