"""add kanban board table

Revision ID: c4f2a8e91b73
Revises: 91c6bdf98313
Create Date: 2026-09-02 10:42:18.114903+00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'c4f2a8e91b73'
down_revision: Union[str, None] = '91c6bdf98313'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'kanban',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            'candidature_id', postgresql.UUID(as_uuid=True), nullable=False,
            comment='One board entry per candidature. CASCADE removes it with the card.',
        ),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            'status', sa.String(length=50), nullable=False,
            comment='Board column: to_send | sent | interview | rejected | accepted',
        ),
        sa.Column(
            'position', sa.Integer(), nullable=False,
            comment='Rank within the column. Ascending, gaps allowed.',
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['candidature_id'], ['candidatures.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('candidature_id'),
        # DEFERRABLE is load-bearing: a move shifts a column with
        # `position = position + 1`, which walks through states where two rows
        # briefly share a position. Deferring to COMMIT lets those through.
        sa.UniqueConstraint(
            'user_id', 'status', 'position',
            name='uq_kanban_user_status_position',
            deferrable=True,
            initially='DEFERRED',
        ),
    )
    op.create_index(op.f('ix_kanban_user_id'), 'kanban', ['user_id'], unique=False)
    op.create_index(
        'ix_kanban_user_status_position', 'kanban', ['user_id', 'status', 'position'], unique=False
    )

    # Backfill: one board entry per existing candidature, ranked oldest-first
    # within each (user, status) column. `candidatures.status` is deliberately
    # kept — see the debt note on app/models/kanban.py.
    op.execute(
        """
        INSERT INTO kanban (id, candidature_id, user_id, status, position, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            c.id,
            c.user_id,
            c.status,
            ROW_NUMBER() OVER (PARTITION BY c.user_id, c.status ORDER BY c.created_at) - 1,
            now(),
            now()
        FROM candidatures c
        """
    )


def downgrade() -> None:
    # candidatures.status was never dropped, so the board table carries no
    # state the rest of the app depends on: dropping it is lossless.
    op.drop_index('ix_kanban_user_status_position', table_name='kanban')
    op.drop_index(op.f('ix_kanban_user_id'), table_name='kanban')
    op.drop_table('kanban')
