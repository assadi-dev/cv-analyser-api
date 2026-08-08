"""Analyse repository."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analyse import Analyse
from app.repositories.base import BaseRepository

if TYPE_CHECKING:
    from app.models.candidature import Candidature


class AnalyseRepository(BaseRepository[Analyse]):
    """Data access layer for Analyse entities."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Analyse, db)

    async def create_analyse(
        self,
        *,
        user_id: uuid.UUID,
        job_description: str,
        cv_text: str | None = None,
        cv_id: uuid.UUID | None = None,
        ai_provider: str = "openai",
        ai_model: str = "gpt-4o",
        score_global: int = 0,
        score_ats: int = 0,
        score_competences: int = 0,
        score_experience: int = 0,
        keywords_found: list[str] | None = None,
        keywords_missing: list[str] | None = None,
        recommandations: list[dict] | None = None,
        conversation_id: uuid.UUID | None = None,
    ) -> Analyse:
        """
        Creates an analysis row.

        Single entry point for both flows. user_id is always required — it is
        what makes the row authorizable. Attaching the analysis to a
        candidature is done afterwards, by setting candidatures.analyse_id.

        Scores default to 0 so the row can be inserted before the pipeline
        runs, then filled in with update_results().
        """
        return await self.create(
            user_id=user_id,
            cv_id=cv_id,
            job_description=job_description,
            cv_text=cv_text,
            score_global=score_global,
            score_ats=score_ats,
            score_competences=score_competences,
            score_experience=score_experience,
            keywords_found=keywords_found if keywords_found is not None else [],
            keywords_missing=keywords_missing if keywords_missing is not None else [],
            recommandations=recommandations if recommandations is not None else [],
            conversation_id=conversation_id,
            ai_provider=ai_provider,
            ai_model=ai_model,
        )

    async def update_results(
        self,
        analyse: Analyse,
        *,
        final_state: dict,
    ) -> Analyse:
        """
        Writes the pipeline output onto an existing row.

        Assigns attributes directly rather than going through
        BaseRepository.update, which skips None values and — more importantly
        here — would drop a legitimate score of 0.
        """
        analyse.score_global = final_state.get("score_global", 0)
        analyse.score_ats = final_state.get("score_ats", 0)
        analyse.score_competences = final_state.get("score_competences", 0)
        analyse.score_experience = final_state.get("score_experience", 0)
        analyse.keywords_found = final_state.get("keywords_found", [])
        analyse.keywords_missing = final_state.get("keywords_missing", [])
        analyse.recommandations = final_state.get("recommandations", [])

        await self.db.flush()
        await self.db.refresh(analyse)
        return analyse

    async def get_for_candidature(
        self, candidature_id: uuid.UUID
    ) -> Analyse | None:
        """
        Returns the analysis attached to a candidature, if any.

        Replaces the former get_latest_for_candidature / list_for_candidature
        pair: the link now lives on candidatures.analyse_id, so a candidature
        points at a single analysis rather than a history of them.
        """
        from app.models.candidature import Candidature

        result = await self.db.execute(
            select(Analyse)
            .join(Candidature, Candidature.analyse_id == Analyse.id)
            .where(Candidature.id == candidature_id)
        )
        return result.scalar_one_or_none()

    async def get_for_conversation(
        self, conversation_id: uuid.UUID
    ) -> Analyse | None:
        """
        Returns the analysis a chat conversation is attached to, if any.

        Reverse lookup: the association is stored on analyses.conversation_id
        only. The unique constraint on that column is what makes
        scalar_one_or_none safe here.
        """
        result = await self.db.execute(
            select(Analyse).where(Analyse.conversation_id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def attach_to_candidature(
        self, analyse: Analyse, candidature: "Candidature"
    ) -> None:
        """Points a candidature at this analysis. Does not commit."""
        candidature.analyse_id = analyse.id
        await self.db.flush()

    async def get_by_user_and_id(
        self,
        user_id: uuid.UUID,
        analyse_id: uuid.UUID,
    ) -> Analyse | None:
        """
        Fetches an analysis owned by the user. Prevents cross-user data access.

        Filters on Analyse.user_id directly: ownership used to be derived by
        joining Candidature, but that inner join now silently hides standalone
        analyses, whose candidature_id is NULL.
        """
        result = await self.db.execute(
            select(Analyse).where(
                and_(
                    Analyse.id == analyse_id,
                    Analyse.user_id == user_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 10,
    ) -> tuple[list[Analyse], int]:
        """All analyses owned by the user, most recent first."""
        return await self.list_all(
            filters=[Analyse.user_id == user_id],
            order_by=Analyse.created_at.desc(),
            offset=offset,
            limit=limit,
        )
