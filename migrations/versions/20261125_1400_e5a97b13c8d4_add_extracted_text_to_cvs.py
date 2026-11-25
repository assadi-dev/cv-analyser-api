"""add extracted_text to cvs

Revision ID: e5a97b13c8d4
Revises: 7d3b1f5a9c20
Create Date: 2026-11-25 14:00:00.000000+00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e5a97b13c8d4'
down_revision: Union[str, None] = '7d3b1f5a9c20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable, no default: CVs uploaded before this column exists have no text
    # yet. The analysis reads their file once and fills it in (CVService.resolve_text).
    op.add_column(
        'cvs',
        sa.Column(
            'extracted_text', sa.Text(), nullable=True,
            comment='Plain text read from the file at upload; analyses use it instead of parsing the file again',
        ),
    )


def downgrade() -> None:
    op.drop_column('cvs', 'extracted_text')
