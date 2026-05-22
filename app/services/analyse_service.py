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
        candidature: Candidature,
        request: AnalyseRequest,
    ) -> AsyncGenerator[dict[str, Any], None]:
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
            candidature:  The candidature being analysed.
            request:      Analysis request body.

        Yields:
            SSE event dicts (progress, result, done, error).
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
        # Step 3 — Build initial graph state
        # ---------------------------------------------------------------
        initial_state = {
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
                "candidature_id": str(candidature.id),
                "provider": preference.ai_provider,
                "model": preference.ai_model,
            },
        )

        # ---------------------------------------------------------------
        # Step 4 — Run graph and yield events
        # ---------------------------------------------------------------
        final_state: dict[str, Any] = {}

        async for step_output in analyse_graph.astream(initial_state):
            # Each step_output is {node_name: state_updates}
            for node_name, updates in step_output.items():
                # Yield any new SSE events produced by this node
                new_events: list[dict] = updates.get("stream_events", [])
                for event in new_events:
                    if event not in initial_state.get("stream_events", []):
                        yield event

                # Merge updates into final_state for persistence
                final_state.update(updates)

        # ---------------------------------------------------------------
        # Step 5 — Persist results
        # ---------------------------------------------------------------
        analyse_repo = AnalyseRepository(self.db)
        analyse = await analyse_repo.create(
            candidature_id=candidature.id,
            cv_id=request.cv_id,
            job_description=request.job_description,
            cv_text=cv_text,
            score_global=final_state.get("score_global", 0),
            score_ats=final_state.get("score_ats", 0),
            score_competences=final_state.get("score_competences", 0),
            score_experience=final_state.get("score_experience", 0),
            keywords_found=final_state.get("keywords_found", []),
            keywords_missing=final_state.get("keywords_missing", []),
            recommandations=final_state.get("recommandations", []),
            chat_history=[],
            ai_provider=preference.ai_provider,
            ai_model=preference.ai_model,
        )

        logger.info(
            "Analysis completed and persisted",
            extra={
                "analyse_id": str(analyse.id),
                "score_global": analyse.score_global,
                "score_ats": analyse.score_ats,
            },
        )

        # ---------------------------------------------------------------
        # Step 6 — Final "done" event
        # ---------------------------------------------------------------
        yield {"type": "done", "analyse_id": str(analyse.id)}

    async def run_stream_cv(self, *, user_id: uuid.UUID, request: AnalyseRequestTemporary) -> AsyncGenerator[dict[str, Any], None]:
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
            cv_text:      The CV text to analyse.
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
        # Step 3 — Build initial graph state
        # ---------------------------------------------------------------
        initial_state = {
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
                "provider": preference.ai_provider,
                "model": preference.ai_model,
            },
        )

        # ---------------------------------------------------------------
        # Step 4 — Run graph and yield events
        # ---------------------------------------------------------------
        final_state: dict[str, Any] = {}

        async for step_output in analyse_graph.astream(initial_state):
            # Each step_output is {node_name: state_updates}
            for node_name, updates in step_output.items():
                # Yield any new SSE events produced by this node
                new_events: list[dict] = updates.get("stream_events", [])
                for event in new_events:
                    if event not in initial_state.get("stream_events", []):
                        yield event

                # Merge updates into final_state for persistence
                final_state.update(updates)

 

        logger.info(
            "Analysis completed",
            extra={
               
                "score_global": final_state.get("score_global", 0),
                "score_ats": final_state.get("score_ats", 0),
            },
        )

        # ---------------------------------------------------------------
        # Step 6 — Final "done" event
        # ---------------------------------------------------------------
        yield {"type": "done"}


    async def chat(self, *, analyse: Analyse, message: str) -> str:
        """
        Continues a conversation with the AI assistant on an existing analysis.

        Args:
            analyse: The Analyse ORM instance.
            message: User's chat message.

        Returns:
            AI assistant reply as a string.
        """
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        preference_repo = PreferenceRepository(self.db)
        # We need the user — get it via candidature
        from app.repositories.candidature_repo import CandidatureRepository
        cand_repo = CandidatureRepository(self.db)
        candidature = await cand_repo.get_by_id_or_raise(analyse.candidature_id)
        preference = await preference_repo.get_by_user_id(candidature.user_id)

        api_key = ""
        if preference.ai_api_key_encrypted:
            api_key = ProviderService.decrypt_api_key(preference.ai_api_key_encrypted)

        llm = ProviderService.get_llm(preference.ai_provider, preference.ai_model, api_key, preference.ai_base_url,settings.llm_temperature)

        system = SystemMessage(
            content=(
                "You are a helpful career coach assistant. "
                f"The user's CV was matched against a job offer with "
                f"a global score of {analyse.score_global}/100 "
                f"and an ATS score of {analyse.score_ats}/100. "
                "Help them improve their application based on the analysis results."
            )
        )

        # Rebuild conversation history
        history_messages = []
        for entry in analyse.chat_history:
            if entry.get("role") == "user":
                history_messages.append(HumanMessage(content=entry["content"]))
            elif entry.get("role") == "assistant":
                history_messages.append(AIMessage(content=entry["content"]))

        history_messages.append(HumanMessage(content=message))

        response = await llm.ainvoke([system, *history_messages])
        reply = str(response.content)

        # Persist chat history
        new_history = [
            *analyse.chat_history,
            {"role": "user", "content": message},
            {"role": "assistant", "content": reply},
        ]
        from app.repositories.analyse_repo import AnalyseRepository
        analyse_repo = AnalyseRepository(self.db)
        await analyse_repo.update(analyse, chat_history=new_history)

        return reply
