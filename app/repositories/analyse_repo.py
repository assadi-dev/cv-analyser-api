"""Analyse repository."""

import uuid

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analyse import Analyse
from app.repositories.base import BaseRepository


class AnalyseRepository(BaseRepository[Analyse]):
    """Data access layer for Analyse entities."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Analyse, db)

    async def get_latest_for_candidature(
        self, candidature_id: uuid.UUID
    ) -> Analyse | None:
        """Returns the most recent analysis for a candidature."""
        result = await self.db.execute(
            select(Analyse)
            .where(Analyse.candidature_id == candidature_id)
            .order_by(Analyse.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_for_candidature(
        self,
        candidature_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 10,
    ) -> tuple[list[Analyse], int]:
        """Returns all analyses for a given candidature."""
        return await self.list_all(
            filters=[Analyse.candidature_id == candidature_id],
            order_by=Analyse.created_at.desc(),
            offset=offset,
            limit=limit,
        )

    async def get_by_user_and_id(
        self,
        user_id: uuid.UUID,
        analyse_id: uuid.UUID,
    ) -> Analyse | None:
        """
        Fetches an analysis owned by the user (via candidature ownership).
        Prevents cross-user data access.
        """
        from app.models.candidature import Candidature

        result = await self.db.execute(
            select(Analyse)
            .join(Candidature, Analyse.candidature_id == Candidature.id)
            .where(
                and_(
                    Analyse.id == analyse_id,
                    Candidature.user_id == user_id,
                )
            )
        )
        return result.scalar_one_or_none()
