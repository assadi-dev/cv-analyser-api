"""Kanban ORM model — board placement for a candidature."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.candidature import Candidature
    from app.models.user import User


class Kanban(BaseModel):
    """
    Board state for a candidature: which column it sits in, and where.

    ---- Design decision (Assadi, 2026-09-02) — accepted technical debt ----

    `status` is duplicated: it lives here AND on `candidatures.status`.
    The single source of truth should be this table, but dropping the
    column on `candidatures` would ripple through the paginated filter,
    `count_by_status`, the creation form and the nuqs status tabs. For
    the POC phase that cost is not worth paying, so both columns are
    kept in sync instead.

    Rules while the duplication stands:

      * `candidatures.status` stays the READ source. API responses and
        filters keep reading it, so the frontend contract is untouched.
      * `kanban.status` + `kanban.position` drive the board only.
      * Every WRITE path must update both, in the same transaction:
            PATCH /{id}         -- CandidatureUpdate may carry `status`
            PATCH /{id}/status  -- select on the /candidatures page
            PATCH /{id}/move    -- drag & drop on the board
        Missing one of the three is how the two columns drift apart.
      * A status change coming from outside the board lands the card at
        the end of its target column (position = max + 1).

    To repay: drop `candidatures.status`, hydrate
    `CandidatureSummary.status` from this relation, and point the
    filter and the counters at this table.

    ---- Positions are NOT contiguous, and that is intentional ----

    Deleting a candidature leaves a hole (0, 1, 3, 4) that is never
    filled back in. Moves are anchored on neighbour ids, so the backend
    only ever compares positions -- `position >= target` is an ordering
    relation, never an array index. Holes cost nothing, so no
    recompaction runs on delete.
    """

    __tablename__ = "kanban"

    __table_args__ = (
        # DEFERRABLE is required, not cosmetic: shifting a column with
        # `position = position + 1` walks through intermediate states where
        # two rows briefly share a position. Deferring the check to COMMIT
        # lets those states through; a plain UNIQUE would abort the move.
        UniqueConstraint(
            "user_id",
            "status",
            "position",
            name="uq_kanban_user_status_position",
            deferrable=True,
            initially="DEFERRED",
        ),
        Index("ix_kanban_user_status_position", "user_id", "status", "position"),
    )

    # -------------------------------------------------------------------------
    # Foreign keys
    # -------------------------------------------------------------------------
    candidature_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidatures.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        comment="One board entry per candidature. CASCADE removes it with the card.",
    )
    # Denormalised from candidatures.user_id. Required: without it neither the
    # unique constraint nor the index above can be expressed on this table, and
    # every shift would have to join candidatures to know which board it edits.
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # -------------------------------------------------------------------------
    # Board placement
    # -------------------------------------------------------------------------
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="to_send",
        comment="Board column: to_send | sent | interview | rejected | accepted",
    )
    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Rank within the column. Ascending, gaps allowed.",
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    candidature: Mapped["Candidature"] = relationship(
        "Candidature", back_populates="kanban"
    )
    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<Kanban id={self.id} candidature={self.candidature_id} "
            f"status={self.status} position={self.position}>"
        )
