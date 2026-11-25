"""add job_description to candidatures

Revision ID: 7d3b1f5a9c20
Revises: c4f2a8e91b73
Create Date: 2026-11-25 12:00:00.000000+00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7d3b1f5a9c20'
down_revision: Union[str, None] = 'c4f2a8e91b73'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable, no default: existing candidatures simply have no offer text.
    op.add_column(
        'candidatures',
        sa.Column(
            'job_description', sa.Text(), nullable=True,
            comment='Job offer text, kept with the application and used to pre-fill analyses',
        ),
    )


def downgrade() -> None:
    op.drop_column('candidatures', 'job_description')
