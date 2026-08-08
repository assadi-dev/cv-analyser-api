"""
Analyse service — orchestrates the LangGraph pipeline with SSE streaming.

Bridges the HTTP layer (FastAPI route) and the AI agent (LangGraph graph).
"""

from app.schemas.analyse import AnalyseRequestTemporary
from app.core.config import settings
from app.repositories.preference_repo import PreferenceRepository
from app.models import Preference
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import analyse_graph
from app.core.exceptions import AIProviderError
from app.core.logging import get_logger
from app.models.analyse import Analyse
from app.models.candidature import Candidature
from app.repositories.analyse_repo import AnalyseRepository
from app.repositories.cv_repo import CVRepository
from app.repositories.user_repo import UserRepository
from app.schemas.analyse import AnalyseRequest
from app.services.cv_parser_services import CVParserService
from app.services.provider_service import ProviderService

logger = get_logger(__name__)


class AnalyseService:
    """Orchestrates AI analysis and persists results."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def run_stream_candidature(
        self,
        *,
        user_id: uuid.UUID,
        candidature: Candidature | None,
        request: AnalyseRequest,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Executes the LangGraph pipeline and yields SSE events.

        Flow:
        1. Resolve CV text (from request or stored file)
        2. Resolve AI provider config for the user
        3. Create the Analyse row (so its id exists from the first event)
        4. Build initial state and run the graph
        5. Yield SSE events progressively
        6. Persist the results onto the row
        7. Yield final "done" event with analyse_id

        Args:
            user_id:      Authenticated user's UUID.
            candidature:  The candidature being analysed, or None for a
                          standalone analysis.
            request:      Analysis request body.

        Yields:
            SSE event dicts (progress, result, done, error), each carrying
            analyse_id.
        """
        # ---------------------------------------------------------------
        # Step 1 — Resolve CV text
        # ---------------------------------------------------------------
        cv_text = request.cv_text

        if not cv_text and request.cv_id:
            cv_repo = CVRepository(self.db)
            cv = await cv_repo.get_by_id(request.cv_id)
            if cv:
                cv_text = CVParserService.parse_file(cv.file_path)

        if not cv_text:
            # Fall back to user's default CV
            cv_repo = CVRepository(self.db)
            default_cv = await cv_repo.get_default_for_user(user_id)
            if default_cv:
                cv_text = CVParserService.parse_file(default_cv.file_path)

        cv_text = cv_text or ""

        # ---------------------------------------------------------------
        # Step 2 — Resolve AI provider config
        # ---------------------------------------------------------------
        preference_repo = PreferenceRepository(self.db)
        preference = await preference_repo.get_by_user_id(user_id)

        api_key = ""
        if preference.ai_api_key_encrypted:
            api_key = ProviderService.decrypt_api_key(preference.ai_api_key_encrypted)

        # ---------------------------------------------------------------
        # Step 3 — Create the analysis row up front
        # ---------------------------------------------------------------
        # Created before the pipeline so its id can travel with every SSE
        # event, and so the graph nodes can reach the row through
        # state["analyse_id"]. Scores are filled in at step 6.
        analyse_repo = AnalyseRepository(self.db)
        analyse = await analyse_repo.create_analyse(
            user_id=user_id,
            cv_id=request.cv_id,
            job_description=request.job_description,
            cv_text=cv_text,
            ai_provider=preference.ai_provider,
            ai_model=preference.ai_model,
        )
        # The association is carried by the candidature, in that direction only.
        # It replaces whatever analysis the candidature pointed at before.
        if candidature is not None:
            await analyse_repo.attach_to_candidature(analyse, candidature)
        await self.db.commit()

        # ---------------------------------------------------------------
        # Step 4 — Build initial graph state
        # ---------------------------------------------------------------
        initial_state = {
            "analyse_id": str(analyse.id),
            "cv_text": cv_text,
            "job_text": request.job_description,
            "provider": preference.ai_provider,
            "model": preference.ai_model,
            "api_key": api_key,
            "language": preference.preferred_language,
            "recommendation_detail": preference.recommendation_detail,
            "job_keywords": [],
            "cv_keywords": [],
            "score_ats": 0,
            "score_competences": 0,
            "score_experience": 0,
            "score_global": 0,
            "keywords_found": [],
            "keywords_missing": [],
            "recommandations": [],
            "stream_events": [],
            "error": None,
        }

        logger.info(
            "Analysis pipeline started",
            extra={
                "user_id": str(user_id),
                "analyse_id": str(analyse.id),
                "candidature_id": str(candidature.id) if candidature else None,
                "provider": preference.ai_provider,
                "model": preference.ai_model,
            },
        )

        # ---------------------------------------------------------------
        # Step 5 — Run graph and yield events
        # ---------------------------------------------------------------
        final_state: dict[str, Any] = {}
        yielded_event_count = 0

        async for step_output in analyse_graph.astream(initial_state):
            for node_name, updates in step_output.items():
                # Each node accumulates all previous events + its own new ones.
                # Slice from where we left off to yield only the new ones.
                all_events: list[dict] = updates.get("stream_events", [])
                for event in all_events[yielded_event_count:]:
                    yield {**event, "analyse_id": str(analyse.id)}
                yielded_event_count = len(all_events)
                final_state.update(updates)

        # ---------------------------------------------------------------
        # Step 6 — Persist the results onto the row created at step 3
        # ---------------------------------------------------------------
        await analyse_repo.update_results(analyse, final_state=final_state)
        await self.db.commit()

        logger.info(
            "Analysis completed and persisted",
            extra={
                "analyse_id": str(analyse.id),
                "score_global": analyse.score_global,
                "score_ats": analyse.score_ats,
            },
        )

        # ---------------------------------------------------------------
        # Step 7 — Final "done" event
        # ---------------------------------------------------------------
        yield {"type": "done", "analyse_id": str(analyse.id)}

    async def run_stream_anonymous(self, *, user_id: uuid.UUID, request: AnalyseRequestTemporary) -> AsyncGenerator[dict[str, Any], None]:
        """
        Executes the LangGraph pipeline and yields SSE events.

        Flow:
        1. Resolve CV text (from request or stored file)
        2. Resolve AI provider config for the user
        3. Build initial state and run the graph
        4. Yield SSE events progressively
        5. Persist results to database
        6. Yield final "done" event with analyse_id

        Args:
            user_id:      Authenticated user's UUID.
            request:      Analysis request body.

        Yields:
            SSE event dicts (progress, result, done, error).
        """
               # ---------------------------------------------------------------
        # Step 1 — Resolve CV text
        # ---------------------------------------------------------------
        cv_text = request.cv_text

        if not cv_text:
            raise ValueError("CV text is required")

        # ---------------------------------------------------------------
        # Step 2 — Resolve AI provider config
        # ---------------------------------------------------------------
        preference_repo = PreferenceRepository(self.db)
        preference = await preference_repo.get_by_user_id(user_id)

        api_key = ""
        if preference.ai_api_key_encrypted:
            api_key = ProviderService.decrypt_api_key(preference.ai_api_key_encrypted)

        # ---------------------------------------------------------------
        # Step 3 — Create the analysis row up front
        # ---------------------------------------------------------------
        # Created before the pipeline runs so the id exists from the first SSE
        # event: the client can attach a chat conversation to it without
        # waiting for the analysis to finish. Scores are filled in at step 6.
        # No candidature is attached — this analysis is standalone.
        analyse_repo = AnalyseRepository(self.db)
        analyse = await analyse_repo.create_analyse(
            user_id=user_id,
            cv_text=cv_text,
            job_description=request.job_description,
            ai_provider=preference.ai_provider,
            ai_model=preference.ai_model,
        )
        await self.db.commit()

        # ---------------------------------------------------------------
        # Step 4 — Build initial graph state
        # ---------------------------------------------------------------
        initial_state = {
            "analyse_id": str(analyse.id),
            "cv_text": cv_text,
            "job_text": request.job_description,
            "provider": preference.ai_provider,
            "model": preference.ai_model,
            "api_key": api_key,
            "language": preference.preferred_language,
            "recommendation_detail": preference.recommendation_detail,
            "job_keywords": [],
            "cv_keywords": [],
            "score_ats": 0,
            "score_competences": 0,
            "score_experience": 0,
            "score_global": 0,
            "keywords_found": [],
            "keywords_missing": [],
            "recommandations": [],
            "stream_events": [],
            "error": None,
        }

        logger.info(
            "Analysis pipeline started",
            extra={
                "user_id": str(user_id),
                "analyse_id": str(analyse.id),
                "provider": preference.ai_provider,
                "model": preference.ai_model,
            },
        )

        # ---------------------------------------------------------------
        # Step 5 — Run graph and yield events
        # ---------------------------------------------------------------
        final_state: dict[str, Any] = {}
        yielded_event_count = 0

        async for step_output in analyse_graph.astream(initial_state):
            for node_name, updates in step_output.items():
                all_events: list[dict] = updates.get("stream_events", [])
                for event in all_events[yielded_event_count:]:
                    yield {**event, "analyse_id": str(analyse.id)}
                yielded_event_count = len(all_events)
                final_state.update(updates)

        # ---------------------------------------------------------------
        # Step 6 — Persist the results onto the row created at step 3
        # ---------------------------------------------------------------
        await analyse_repo.update_results(analyse, final_state=final_state)
        await self.db.commit()

        logger.info(
            "Analysis completed and persisted",
            extra={
                "analyse_id": str(analyse.id),
                "score_global": analyse.score_global,
                "score_ats": analyse.score_ats,
            },
        )

        # ---------------------------------------------------------------
        # Step 7 — Final "done" event
        # ---------------------------------------------------------------
        yield {"type": "done", "analyse_id": str(analyse.id)}
