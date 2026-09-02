"""conversation id as uuid fk

Revision ID: 2be9b01d0c13
Revises: 457795f07ce0
Create Date: 2026-08-08 21:10:57.258840+00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '2be9b01d0c13'
down_revision: Union[str, None] = '457795f07ce0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Clear any value that is not a well-formed UUID or no longer points at an
    # existing conversation: both would make the cast or the FK fail. The
    # column only ever held conversation ids, so nothing meaningful is lost.
    op.execute(
        """
        UPDATE analyses
        SET conversation_id = NULL
        WHERE conversation_id IS NOT NULL
          AND (
            conversation_id !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
            OR NOT EXISTS (
                SELECT 1 FROM chat_conversations c
                WHERE c.id::text = analyses.conversation_id
            )
          )
        """
    )

    # postgresql_using is mandatory: Postgres refuses to cast varchar to uuid
    # implicitly.
    op.alter_column(
        'analyses', 'conversation_id',
        existing_type=sa.VARCHAR(length=64),
        type_=sa.UUID(),
        postgresql_using='conversation_id::uuid',
        comment='Chat conversation attached to this analysis, if any',
        existing_comment='Id of the chat conversation attached to this analysis, if any',
        existing_nullable=True,
    )
    op.create_index(
        op.f('ix_analyses_conversation_id'), 'analyses', ['conversation_id'], unique=False
    )
    op.create_foreign_key(
        'fk_analyses_conversation_id', 'analyses', 'chat_conversations',
        ['conversation_id'], ['id'], ondelete='SET NULL', use_alter=True,
    )


def downgrade() -> None:
    op.drop_constraint('fk_analyses_conversation_id', 'analyses', type_='foreignkey')
    op.drop_index(op.f('ix_analyses_conversation_id'), table_name='analyses')
    op.alter_column(
        'analyses', 'conversation_id',
        existing_type=sa.UUID(),
        type_=sa.VARCHAR(length=64),
        postgresql_using='conversation_id::text',
        comment='Id of the chat conversation attached to this analysis, if any',
        existing_comment='Chat conversation attached to this analysis, if any',
        existing_nullable=True,
    )
