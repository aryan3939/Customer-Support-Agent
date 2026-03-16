"""add_resolved_by

Revision ID: 0001
Revises: 
Create Date: 2026-02-18

Manual migration — adds resolved_by column to tickets table.
Written manually because Alembic autogenerate has a timezone
rendering bug with existing TIMESTAMPTZ columns on this setup.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'tickets',
        sa.Column(
            'resolved_by',
            sa.String(50),
            nullable=True,
            comment='Who resolved: customer, admin, or ai_agent',
        ),
    )


def downgrade() -> None:
    op.drop_column('tickets', 'resolved_by')
