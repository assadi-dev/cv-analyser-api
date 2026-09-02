"""Candidature repository."""

import uuid

from sqlalchemy import and_, func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidature import Candidature
from app.models.kanban import Kanban
from app.repositories.base import BaseRepository


class CandidatureRepository(BaseRepository[Candidature]):
    """Data access layer for Candidature entities."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Candidature, db)


    async def create_candidature(self, candidature: Candidature) -> Candidature:
        """
        Creates a candidature for a user.

        Flushes rather than commits: the caller also has to create the matching
        kanban entry, and both must land in the same transaction. `get_db`
        commits at the end of the request, or rolls the whole thing back.
        """
        self.db.add(candidature)
        await self.db.flush()
        await self.db.refresh(candidature)
        return candidature

    async def get_with_contacts(self, candidature_id: uuid.UUID) -> Candidature | None:
        """Fetches a candidature with its contacts eagerly loaded."""
        result = await self.db.execute(
            select(Candidature)
            .options(selectinload(Candidature.contacts))
            .where(Candidature.id == candidature_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        status: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Candidature], int]:
        """
        Returns paginated candidatures for a user, optionally filtered by status.

        Ordered by board position so the Kanban and the list view agree on
        the order of a column. The filter still reads `candidatures.status`,
        not `kanban.status` — see the debt note on app/models/kanban.py.

        The join is a LEFT OUTER: a candidature whose board entry is missing
        (created before this table existed, or by a partial write) still shows
        up, sorted last rather than vanishing from the list.

        Args:
            user_id: Owner's UUID.
            status:  Optional status filter (e.g. "sent", "interview").
            offset:  Pagination offset.
            limit:   Pagination limit.
        """
        filters = [Candidature.user_id == user_id]
        if status:
            filters.append(Candidature.status == status)

        query = (
            select(Candidature)
            .outerjoin(Kanban, Kanban.candidature_id == Candidature.id)
            .where(and_(*filters))
            .order_by(
                Kanban.position.asc().nulls_last(),
                Candidature.created_at.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        count_query = (
            select(func.count())
            .select_from(Candidature)
            .where(and_(*filters))
        )

        items_result = await self.db.execute(query)
        count_result = await self.db.execute(count_query)

        return list(items_result.scalars().all()), count_result.scalar_one()

    async def get_by_user_and_id(
        self,
        user_id: uuid.UUID,
        candidature_id: uuid.UUID,
    ) -> Candidature | None:
        """
        Fetches a candidature only if it belongs to the specified user.
        Prevents cross-user data access.
        """
        result = await self.db.execute(
            select(Candidature)
            .options(selectinload(Candidature.contacts))
            .where(
                and_(
                    Candidature.id == candidature_id,
                    Candidature.user_id == user_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def count_by_status(self, user_id: uuid.UUID) -> dict[str, int]:
        """Returns the count of candidatures per status for a user."""
        from sqlalchemy import func
        result = await self.db.execute(
            select(Candidature.status, func.count(Candidature.id))
            .where(Candidature.user_id == user_id)
            .group_by(Candidature.status)
        )
        return {row[0]: row[1] for row in result.all()}


    async def delete_all_user_candidature(self, user_id: uuid.UUID) -> None:
        """Deletes all candidatures for a user."""
        await self.db.execute(
            delete(Candidature)
            .where(Candidature.user_id == user_id)
        )
        await self.db.commit()

    
