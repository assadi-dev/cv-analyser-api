"""analyse belongs to user, candidature optional

Revision ID: bb14a36ae10b
Revises: e7f736d6a548
Create Date: 2026-08-08 20:51:23.614456+00:00

Ownership of an analysis used to be derived by joining candidatures. Standalone
("temporary") analyses have no candidature, so ownership moves onto the row
itself: user_id is added and backfilled from the candidature, and
candidature_id becomes nullable.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'bb14a36ae10b'
down_revision: Union[str, None] = 'e7f736d6a548'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Added nullable first: existing rows have no value yet, so a NOT NULL
    # column would be rejected outright.
    op.add_column(
        'analyses',
        sa.Column(
            'user_id',
            sa.UUID(),
            nullable=True,
            comment='Owner of the analysis — set even when there is no candidature',
        ),
    )

    # Backfill from the candidature that used to carry the ownership.
    op.execute(
        """
        UPDATE analyses a
        SET user_id = c.user_id
        FROM candidatures c
        WHERE c.id = a.candidature_id
        """
    )

    # Any row whose candidature vanished cannot be attributed to anyone and
    # would block the NOT NULL constraint. There is no owner to guess.
    op.execute("DELETE FROM analyses WHERE user_id IS NULL")

    op.alter_column('analyses', 'user_id', existing_type=sa.UUID(), nullable=False)

    op.alter_column(
        'analyses', 'candidature_id',
        existing_type=sa.UUID(),
        nullable=True,
        comment='Null for standalone (temporary) analyses',
    )
    op.create_index(op.f('ix_analyses_user_id'), 'analyses', ['user_id'], unique=False)
    op.create_foreign_key(
        'fk_analyses_user_id_users', 'analyses', 'users', ['user_id'], ['id'],
        ondelete='CASCADE',
    )


def downgrade() -> None:
    # Standalone analyses cannot exist without candidature_id: drop them before
    # restoring the NOT NULL constraint.
    op.execute("DELETE FROM analyses WHERE candidature_id IS NULL")

    op.drop_constraint('fk_analyses_user_id_users', 'analyses', type_='foreignkey')
    op.drop_index(op.f('ix_analyses_user_id'), table_name='analyses')
    op.alter_column(
        'analyses', 'candidature_id',
        existing_type=sa.UUID(),
        nullable=False,
        comment=None,
        existing_comment='Null for standalone (temporary) analyses',
    )
    op.drop_column('analyses', 'user_id')
