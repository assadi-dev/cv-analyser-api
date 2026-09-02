"""move analyse link onto candidatures

Revision ID: 8a124a2d9574
Revises: f4ca6d4234ac
Create Date: 2026-08-08 21:33:58.885892+00:00

The analyses <-> candidatures association moves from analyses.candidature_id to
candidatures.analyse_id. This changes the cardinality: a candidature used to
own a history of analyses, it now points at a single one — the most recent is
kept, the others survive as standalone analyses owned by the user.

The delete behaviour changes with it: deleting a candidature used to CASCADE
onto its analyses; the new FK is ON DELETE SET NULL, so the analysis outlives
the candidature.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '8a124a2d9574'
down_revision: Union[str, None] = 'f4ca6d4234ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # New column first — the old one is still needed to backfill from.
    op.add_column(
        'candidatures',
        sa.Column(
            'analyse_id', sa.UUID(), nullable=True,
            comment='AI analysis attached to this application, if any',
        ),
    )

    # Keep the most recent analysis of each candidature.
    op.execute(
        """
        UPDATE candidatures c
        SET analyse_id = latest.id
        FROM (
            SELECT DISTINCT ON (candidature_id) candidature_id, id
            FROM analyses
            WHERE candidature_id IS NOT NULL
            ORDER BY candidature_id, created_at DESC
        ) AS latest
        WHERE latest.candidature_id = c.id
        """
    )

    op.create_index(
        op.f('ix_candidatures_analyse_id'), 'candidatures', ['analyse_id'], unique=False
    )
    op.create_foreign_key(
        'fk_candidatures_analyse_id', 'candidatures', 'analyses',
        ['analyse_id'], ['id'], ondelete='SET NULL',
    )

    op.drop_index(op.f('ix_analyses_candidature_id'), table_name='analyses')
    op.drop_constraint(op.f('analyses_candidature_id_fkey'), 'analyses', type_='foreignkey')
    op.drop_column('analyses', 'candidature_id')


def downgrade() -> None:
    op.add_column(
        'analyses',
        sa.Column(
            'candidature_id', sa.UUID(), autoincrement=False, nullable=True,
            comment='Null for standalone (temporary) analyses',
        ),
    )
    op.create_foreign_key(
        op.f('analyses_candidature_id_fkey'), 'analyses', 'candidatures',
        ['candidature_id'], ['id'], ondelete='CASCADE',
    )
    op.create_index(
        op.f('ix_analyses_candidature_id'), 'analyses', ['candidature_id'], unique=False
    )

    # Rebuild the link in the old direction before dropping the new column.
    op.execute(
        """
        UPDATE analyses a
        SET candidature_id = c.id
        FROM candidatures c
        WHERE c.analyse_id = a.id
        """
    )

    op.drop_constraint('fk_candidatures_analyse_id', 'candidatures', type_='foreignkey')
    op.drop_index(op.f('ix_candidatures_analyse_id'), table_name='candidatures')
    op.drop_column('candidatures', 'analyse_id')
