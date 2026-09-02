"""replace analyses chat history by conversation id

Revision ID: 457795f07ce0
Revises: bb14a36ae10b
Create Date: 2026-08-08 21:03:06.982699+00:00

chat_history was only ever written by AnalyseService.chat, which no route
called — the column is empty on every row, so dropping it loses nothing.
Conversations now live in chat_conversations/chat_messages; analyses keep a
pointer to the thread they started.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '457795f07ce0'
down_revision: Union[str, None] = 'bb14a36ae10b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'analyses',
        sa.Column(
            'conversation_id', sa.String(length=64), nullable=True,
            comment='Id of the chat conversation attached to this analysis, if any',
        ),
    )

    # Backfill from the reverse link already recorded on the conversation.
    op.execute(
        """
        UPDATE analyses a
        SET conversation_id = c.id::text
        FROM chat_conversations c
        WHERE c.analyse_id = a.id
        """
    )

    op.drop_column('analyses', 'chat_history')


def downgrade() -> None:
    # server_default is required here: the column is NOT NULL and the table
    # already has rows, so adding it without a default would be rejected.
    op.add_column(
        'analyses',
        sa.Column(
            'chat_history', postgresql.JSON(astext_type=sa.Text()),
            autoincrement=False, nullable=False,
            server_default=sa.text("'[]'::json"),
            comment='DEPRECATED - superseded by chat_conversations/chat_messages',
        ),
    )
    op.drop_column('analyses', 'conversation_id')
