"""phase_12_agent_analyses

Revision ID: a3ea98c9cdec
Revises: 4e9944abe5bf
Create Date: 2026-09-17 13:55:08.449414

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3ea98c9cdec'
down_revision: Union[str, Sequence[str], None] = '4e9944abe5bf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'agent_analyses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recommendation_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('call', sa.String(length=15), nullable=False),
        sa.Column('confidence', sa.Integer(), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=False),
        sa.Column('model', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.CheckConstraint(
            "role IN ('FUNDAMENTAL_ANALYST', 'TECHNICAL_ANALYST', 'PORTFOLIO_MANAGER')",
            name='ck_agent_analyses_role',
        ),
        sa.CheckConstraint(
            "call IN ('BULLISH', 'BEARISH', 'NEUTRAL', 'UNAVAILABLE')",
            name='ck_agent_analyses_call',
        ),
        sa.ForeignKeyConstraint(['recommendation_id'], ['recommendations.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('recommendation_id', 'role', name='uq_agent_analyses_recommendation_role'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('agent_analyses')
