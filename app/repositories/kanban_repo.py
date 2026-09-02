"""Kanban repository — board placement reads and writes."""

import uuid

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kanban import Kanban
from app.repositories.base import BaseRepository


class KanbanRepository(BaseRepository[Kanban]):
    """Data access layer for Kanban board entries."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Kanban, db)

    # -------------------------------------------------------------------------
    # Reads
    # -------------------------------------------------------------------------

    async def get_by_candidature(
        self,
        user_id: uuid.UUID,
        candidature_id: uuid.UUID,
    ) -> Kanban | None:
        """
        Fetches the board entry of a candidature, scoped to its owner.
        Prevents cross-user board access.
        """
        result = await self.db.execute(
            select(Kanban).where(
                and_(
                    Kanban.candidature_id == candidature_id,
                    Kanban.user_id == user_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def next_position(self, user_id: uuid.UUID, status: str) -> int:
        """
        Returns the position that appends a card to the end of a column.

        Positions have gaps (deletions are never recompacted), so this is
        `max + 1`, not `count`.
        """
        result = await self.db.execute(
            select(func.max(Kanban.position)).where(
                and_(Kanban.user_id == user_id, Kanban.status == status)
            )
        )
        current_max = result.scalar_one_or_none()
        return 0 if current_max is None else current_max + 1

    # -------------------------------------------------------------------------
    # Writes
    # -------------------------------------------------------------------------

    async def create_entry(
        self,
        candidature_id: uuid.UUID,
        user_id: uuid.UUID,
        status: str,
    ) -> Kanban:
        """Creates the board entry of a new candidature, at the end of its column."""
        entry = Kanban(
            candidature_id=candidature_id,
            user_id=user_id,
            status=status,
            position=await self.next_position(user_id, status),
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def set_status(self, entry: Kanban, status: str) -> Kanban:
        """
        Moves a card to another column from outside the board — the status
        select on the /candidatures page, or a generic candidature update.

        There is no drop index in that context, so the card lands at the end
        of its target column. A no-op when the status does not change, so the
        card keeps its rank.
        """
        if entry.status == status:
            return entry

        entry.position = await self.next_position(entry.user_id, status)
        entry.status = status
        await self.db.flush()
        return entry

    async def move(
        self,
        entry: Kanban,
        status: str,
        before_id: uuid.UUID | None,
        after_id: uuid.UUID | None,
    ) -> Kanban:
        """
        Places a card at an explicit rank, anchored on its future neighbours.

        `before_id` / `after_id` are the *candidature* ids of the cards framing
        the drop point, as reported by the board. `after_id` is the primary
        anchor; `before_id` only matters when dropping at the end of a column.

        Positions are compared, never treated as array indices, so the gaps
        left by deletions are harmless. One shift statement covers every case
        — including a move down within the same column, because the card being
        moved leaves its own hole behind rather than compacting the column.
        """
        target = await self._resolve_target(entry.user_id, status, before_id, after_id)

        # Open a slot at `target`. The moved card is excluded so it does not
        # shift itself. Transient duplicate positions are absorbed by the
        # DEFERRABLE unique constraint, checked at COMMIT.
        await self.db.execute(
            update(Kanban)
            .where(
                and_(
                    Kanban.user_id == entry.user_id,
                    Kanban.status == status,
                    Kanban.position >= target,
                    Kanban.id != entry.id,
                )
            )
            .values(position=Kanban.position + 1)
        )

        entry.status = status
        entry.position = target
        await self.db.flush()
        return entry

    # -------------------------------------------------------------------------
    # Internals
    # -------------------------------------------------------------------------

    async def _resolve_target(
        self,
        user_id: uuid.UUID,
        status: str,
        before_id: uuid.UUID | None,
        after_id: uuid.UUID | None,
    ) -> int:
        """
        Turns a pair of neighbours into the position the card should take.

            after_id given  -> the card takes that neighbour's position
            after_id null   -> dropped at the end, just past `before_id`
            both null       -> empty column

        Neighbours that do not belong to this user's column are ignored rather
        than trusted: the board may be working from a stale cache.
        """
        if after_id is not None:
            after = await self._neighbour_position(user_id, status, after_id)
            if after is not None:
                return after

        if before_id is not None:
            before = await self._neighbour_position(user_id, status, before_id)
            if before is not None:
                return before + 1

        return await self.next_position(user_id, status)

    async def _neighbour_position(
        self,
        user_id: uuid.UUID,
        status: str,
        candidature_id: uuid.UUID,
    ) -> int | None:
        """Reads a neighbour's live position, or None if it is not in that column."""
        result = await self.db.execute(
            select(Kanban.position).where(
                and_(
                    Kanban.user_id == user_id,
                    Kanban.status == status,
                    Kanban.candidature_id == candidature_id,
                )
            )
        )
        return result.scalar_one_or_none()
