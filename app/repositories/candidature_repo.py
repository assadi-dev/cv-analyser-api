"""Candidature repository."""

import uuid

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidature import Candidature
from app.repositories.base import BaseRepository


class CandidatureRepository(BaseRepository[Candidature]):
    """Data access layer for Candidature entities."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Candidature, db)

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

        Args:
            user_id: Owner's UUID.
            status:  Optional status filter (e.g. "sent", "interview").
            offset:  Pagination offset.
            limit:   Pagination limit.
        """
        filters = [Candidature.user_id == user_id]
        if status:
            filters.append(Candidature.status == status)

        return await self.list_all(
            filters=filters,
            order_by=Candidature.created_at.desc(),
            offset=offset,
            limit=limit,
        )

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
