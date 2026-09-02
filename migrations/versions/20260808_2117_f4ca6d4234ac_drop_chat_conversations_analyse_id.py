"""drop chat conversations analyse id

Revision ID: f4ca6d4234ac
Revises: 2be9b01d0c13
Create Date: 2026-08-08 21:17:21.811510+00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f4ca6d4234ac'
down_revision: Union[str, None] = '2be9b01d0c13'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nothing to migrate: analyses.conversation_id already carries the same
    # association, in the only direction kept from now on.
    op.drop_index(op.f('ix_chat_conversations_analyse_id'), table_name='chat_conversations')
    op.drop_constraint(
        op.f('chat_conversations_analyse_id_fkey'), 'chat_conversations', type_='foreignkey'
    )
    op.drop_column('chat_conversations', 'analyse_id')


def downgrade() -> None:
    op.add_column(
        'chat_conversations',
        sa.Column(
            'analyse_id', sa.UUID(), autoincrement=False, nullable=True,
            comment='Analyse this conversation was started from, when persisted',
        ),
    )
    op.create_foreign_key(
        op.f('chat_conversations_analyse_id_fkey'), 'chat_conversations', 'analyses',
        ['analyse_id'], ['id'], ondelete='SET NULL',
    )
    op.create_index(
        op.f('ix_chat_conversations_analyse_id'), 'chat_conversations', ['analyse_id'],
        unique=False,
    )

    # Rebuild the reverse link from the surviving direction, otherwise the
    # restored column would come back empty.
    op.execute(
        """
        UPDATE chat_conversations c
        SET analyse_id = a.id
        FROM analyses a
        WHERE a.conversation_id = c.id
        """
    )
