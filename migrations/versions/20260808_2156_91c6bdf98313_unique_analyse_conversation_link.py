"""unique analyse conversation link

Revision ID: 91c6bdf98313
Revises: 8a124a2d9574
Create Date: 2026-08-08 21:56:34.536277+00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '91c6bdf98313'
down_revision: Union[str, None] = '8a124a2d9574'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The old index was non-unique, so duplicates may already exist and would
    # make the constraint fail. Keep the most recent analysis of each
    # conversation and unlink the others.
    op.execute(
        """
        UPDATE analyses
        SET conversation_id = NULL
        WHERE conversation_id IS NOT NULL
          AND id NOT IN (
            SELECT DISTINCT ON (conversation_id) id
            FROM analyses
            WHERE conversation_id IS NOT NULL
            ORDER BY conversation_id, created_at DESC
          )
        """
    )

    op.drop_index(op.f('ix_analyses_conversation_id'), table_name='analyses')
    # Postgres allows any number of NULLs under a unique constraint, so
    # analyses without a conversation are unaffected. The constraint also
    # provides the index the reverse lookup needs.
    op.create_unique_constraint(
        'uq_analyses_conversation_id', 'analyses', ['conversation_id']
    )


def downgrade() -> None:
    op.drop_constraint('uq_analyses_conversation_id', 'analyses', type_='unique')
    op.create_index(
        op.f('ix_analyses_conversation_id'), 'analyses', ['conversation_id'], unique=False
    )
