"""add chat conversations and messages

Revision ID: e7f736d6a548
Revises: 801b9ea3892e
Create Date: 2026-08-08 18:42:11.400751+00:00

Note: autogenerate also proposed dropping the `user`, `session`, `account` and
`verification` tables. Those belong to better-auth on the Next.js side, they are
not part of Base.metadata, and dropping them would destroy every login. The
generated drop/create statements for them were removed by hand.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'e7f736d6a548'
down_revision: Union[str, None] = '801b9ea3892e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'chat_conversations',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('analyse_id', sa.UUID(), nullable=True, comment='Analyse this conversation was started from, when persisted'),
        sa.Column('cv_text', sa.Text(), nullable=True, comment='CV text the assistant reasons on'),
        sa.Column('job_description', sa.Text(), nullable=True, comment='Job offer text the assistant reasons on'),
        sa.Column('score_global', sa.Integer(), nullable=True, comment='Match score (0-100) given to the model'),
        sa.Column('recommandations', postgresql.JSON(astext_type=sa.Text()), nullable=False, comment='Snapshot of the analysis recommendations (same shape as analyses.recommandations)'),
        sa.Column('title', sa.String(length=255), nullable=False, comment='Derived from the first question; user-editable'),
        sa.Column('last_message_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment="Denormalised for cheap 'most recent first' ordering"),
        sa.Column('message_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('is_archived', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('ai_provider', sa.String(length=50), nullable=False),
        sa.Column('ai_model', sa.String(length=100), nullable=False),
        sa.Column('language', sa.String(length=10), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['analyse_id'], ['analyses.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_chat_conversations_analyse_id'), 'chat_conversations', ['analyse_id'], unique=False)
    op.create_index(op.f('ix_chat_conversations_user_id'), 'chat_conversations', ['user_id'], unique=False)
    op.create_index('ix_chat_conversations_user_last_message', 'chat_conversations', ['user_id', 'last_message_at'], unique=False)

    op.create_table(
        'chat_messages',
        sa.Column('conversation_id', sa.UUID(), nullable=False),
        sa.Column('seq', sa.Integer(), nullable=False, comment='0-based position of the message inside its conversation'),
        sa.Column('role', sa.String(length=20), nullable=False, comment='user | assistant'),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_partial', sa.Boolean(), server_default='false', nullable=False, comment='True when the client disconnected before the answer was complete'),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['chat_conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('conversation_id', 'seq', name='uq_chat_messages_conv_seq'),
    )
    op.create_index(op.f('ix_chat_messages_conversation_id'), 'chat_messages', ['conversation_id'], unique=False)
    op.create_index('ix_chat_messages_conversation_seq', 'chat_messages', ['conversation_id', 'seq'], unique=False)

    op.alter_column(
        'analyses', 'chat_history',
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        comment='DEPRECATED - superseded by chat_conversations/chat_messages',
        existing_comment='Conversation history with the AI assistant',
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        'analyses', 'chat_history',
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        comment='Conversation history with the AI assistant',
        existing_comment='DEPRECATED - superseded by chat_conversations/chat_messages',
        existing_nullable=False,
    )

    # chat_messages first: it holds the FK to chat_conversations.
    op.drop_index('ix_chat_messages_conversation_seq', table_name='chat_messages')
    op.drop_index(op.f('ix_chat_messages_conversation_id'), table_name='chat_messages')
    op.drop_table('chat_messages')

    op.drop_index('ix_chat_conversations_user_last_message', table_name='chat_conversations')
    op.drop_index(op.f('ix_chat_conversations_user_id'), table_name='chat_conversations')
    op.drop_index(op.f('ix_chat_conversations_analyse_id'), table_name='chat_conversations')
    op.drop_table('chat_conversations')
