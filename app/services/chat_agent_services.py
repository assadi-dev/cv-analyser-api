import asyncio
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any

import anyio

from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.agent_chat import AgentChatState, agent_chat_graph
from app.core.database import AsyncSessionFactory
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models.chat_conversation import ChatConversation
from app.models.chat_message import ChatMessage
from app.repositories.analyse_repo import AnalyseRepository
from app.repositories.chat_conversation_repo import ChatConversationRepository
from app.repositories.preference_repo import PreferenceRepository
from app.schemas.chat import ChatStreamRequest
from app.services.provider_service import ProviderService

logger = get_logger(__name__)

# _format_history injects the whole transcript into the system prompt, next to
# the full CV and job description. Without a cap, both the cost and the context
# window grow without bound as a thread gets longer.
HISTORY_WINDOW = 20

_ROLE_TO_MESSAGE = {"user": HumanMessage, "assistant": AIMessage}


def _chunk_text(chunk: Any) -> str:
    """
    Extrait le texte d'un chunk de message.

    Le contenu est une simple chaîne chez OpenAI/Groq/Mistral, mais une liste de
    blocs ({"type": "text", "text": ...}) chez Anthropic — d'où la normalisation.
    """
    content = getattr(chunk, "content", "")

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        return "".join(
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        )

    return ""


def _utc_timestamp() -> str:
    """Current UTC time, as the 'YYYY-MM-DD HH:MM:SS' string the client expects."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _chat_event(
    event_type: str,
    *,
    conversation_id: uuid.UUID,
    message_id: uuid.UUID | None = None,
    chunk: str | None = None,
    content: str = "",
    message: str | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    """
    Builds one SSE frame.

    Single place where the wire format is defined, so start / token / complete
    / error cannot drift apart.
    """
    event: dict[str, Any] = {
        "type": event_type,
        "conversation_id": str(conversation_id),
        "message": message,
        "complete": event_type == "complete",
    }

    if error is not None:
        event["error"] = error

    if message_id is not None:
        event["data"] = {
            "id": str(message_id),
            "chunk": chunk,
            "content": content,
            "role": "assistant",
            "timestamp": _utc_timestamp(),
        }

    return event


def _to_lc_messages(rows: list[ChatMessage]) -> list[BaseMessage]:
    """
    Rehydrates stored rows into LangChain message objects.

    Objects, not dicts: _format_history in agent_chat.py branches on
    isinstance(msg, HumanMessage) to label each line of the transcript.
    """
    return [
        _ROLE_TO_MESSAGE[row.role](content=row.content)
        for row in rows
        if row.role in _ROLE_TO_MESSAGE and row.content
    ]


def _format_recommendations(recommandations: list[dict[str, Any]] | None) -> str:
    """
    Renders the recommendations for the prompt.

    AgentChatState.recommendations is typed str and interpolated straight into
    an f-string, so handing over a list would dump a Python repr into the prompt.
    """
    if not recommandations:
        return "(aucune recommandation disponible)"

    lines = []
    for item in recommandations:
        if not isinstance(item, dict):
            lines.append(f"- {item}")
            continue
        title = item.get("title", "")
        description = item.get("description", "")
        lines.append(f"- {title} : {description}" if title else f"- {description}")

    return "\n".join(lines)


class ChatAgentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = get_logger(__name__)

    # -------------------------------------------------------------------------
    # Phase 1 — resolve the conversation (runs before the response starts)
    # -------------------------------------------------------------------------
    async def open_conversation(
        self, user_id: uuid.UUID, body: ChatStreamRequest
    ) -> tuple[ChatConversation, int]:
        """
        Resumes or creates a conversation, then stores the user's question.

        Called from the route BEFORE the StreamingResponse is built: that is
        what lets a missing conversation surface as a real HTTP 404 instead of
        an SSE error frame sent after a 200 has already gone out.

        Returns the conversation and the seq of the message just inserted.
        """
        repo = ChatConversationRepository(self.db)

        cv_text = body.cv_text or ""
        job_description = body.job_description or ""
        score_global = body.score_global or None
        recommandations = body.recommandations or []
        analyse_id = body.analyse_id or None

        if body.conversation_id is not None:
            conversation = await repo.get_for_user(body.conversation_id, user_id)
            if conversation is None:
                # NotFoundError rather than ForbiddenError: a 403 would confirm
                # the existence of another user's conversation.
                raise NotFoundError(
                    resource="ChatConversation",
                    resource_id=str(body.conversation_id),
                )
        else:
            preference_repo = PreferenceRepository(self.db)
            preference = await preference_repo.get_by_user_id(user_id)
            if preference is None:
                raise NotFoundError(resource="Preference", resource_id=str(user_id))

            # An analyse_id coming from the client must be proven to belong to
            # the caller before we write the link onto that row.
            analyse = None
            if body.analyse_id is not None:
                analyse_repo = AnalyseRepository(self.db)
                analyse = await analyse_repo.get_by_user_and_id(user_id, body.analyse_id)
                if analyse is None:
                    raise NotFoundError(
                        resource="Analyse", resource_id=str(body.analyse_id)
                    )
                
                cv_text = analyse.cv_text
                job_description = analyse.job_description
                score_global = analyse.score_global
                recommandations = analyse.recommandations

            conversation = await repo.create(
                user_id=user_id,
                title=body.question[:255],
                cv_text=cv_text,
                job_description=job_description,
                score_global=score_global,
                recommandations=recommandations,
                ai_provider=preference.ai_provider,
                ai_model=preference.ai_model,
                language=preference.preferred_language,
            )

            # The association lives on the analysis side, and only there.
            if analyse is not None:
                analyse.conversation_id = conversation.id

        user_message = await repo.add_message(
            conversation.id, role="user", content=body.question
        )
        await repo.touch(conversation, message_delta=1)

        # T1 — the question is durable before any LLM call is made.
        await self.db.commit()

        return conversation, user_message.seq

    # -------------------------------------------------------------------------
    # Context resolution
    # -------------------------------------------------------------------------
    async def _resolve_context(
        self, conversation: ChatConversation
    ) -> dict[str, Any]:
        """
        Returns the analysis context the prompt is built from.

        The analysis attached to this conversation wins when there is one, so
        the thread always reasons on the live scores and recommendations. The
        snapshot stored on the conversation is only a fallback, for threads
        started without any analysis.

        Note the consequence of reading live: re-running the analysis changes
        the context of a conversation already under way.
        """
        analyse = await AnalyseRepository(self.db).get_for_conversation(
            conversation.id
        )

        if analyse is not None:
            return {
                "cv_text": analyse.cv_text,
                "job_description": analyse.job_description,
                "score_global": analyse.score_global,
                "recommandations": analyse.recommandations,
                "source": "analyse",
            }

        return {
            "cv_text": conversation.cv_text,
            "job_description": conversation.job_description,
            "score_global": conversation.score_global,
            "recommandations": conversation.recommandations,
            "source": "snapshot",
        }

    # -------------------------------------------------------------------------
    # Phase 2 — stream the answer
    # -------------------------------------------------------------------------
    async def stream_chat(
        self,
        conversation: ChatConversation,
        question: str,
        user_seq: int,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Exécute le graphe de chat et émet les événements SSE au fil de l'eau.

        Forme des frames (start → token* → complete, ou error) :

            {
              "type": "start" | "token" | "complete" | "error",
              "conversation_id": str,
              "message": str | None,      # réponse finale sur "complete"
              "error": str,               # sur "error" uniquement
              "complete": bool,           # true sur "complete"
              "data": {
                "id": str,                # id du ChatMessage en base
                "chunk": str | None,      # fragment de cet événement
                "content": str,           # contenu accumulé jusqu'ici
                "role": "assistant",
                "timestamp": "YYYY-MM-DD HH:MM:SS"   # UTC
              }
            }
        """
        repo = ChatConversationRepository(self.db)
        preference_repo = PreferenceRepository(self.db)

        preference = await preference_repo.get_by_user_id(conversation.user_id)
        if preference is None:
            raise NotFoundError(
                resource="Preference", resource_id=str(conversation.user_id)
            )

        api_key = ""
        if preference.ai_api_key_encrypted:
            api_key = ProviderService.decrypt_api_key(preference.ai_api_key_encrypted)

        # before_seq excludes the turn being answered: the graph adds it itself
        # via user_message, and including it would repeat the question twice in
        # the prompt.
        history = await repo.recent_messages(
            conversation.id, limit=HISTORY_WINDOW, before_seq=user_seq
        )

        context = await self._resolve_context(conversation)

        initial_state = AgentChatState(
            language=conversation.language,
            provider=conversation.ai_provider,
            model=conversation.ai_model,
            api_key=api_key,
            recommendations=_format_recommendations(context["recommandations"]),
            score=str(context["score_global"])
            if context["score_global"] is not None
            else "non calculé",
            job_description=context["job_description"] or "",
            cv=context["cv_text"] or "",
            messages=_to_lc_messages(history),
            user_message=question,
        )

        # Ne jamais logger initial_state tel quel : il contient la clé API en clair.
        self.logger.info(
            "Chat stream started",
            extra={
                "conversation_id": str(conversation.id),
                "user_id": str(conversation.user_id),
                "provider": conversation.ai_provider,
                "model": conversation.ai_model,
                "history_messages": len(history),
                "context_source": context["source"],
            },
        )

        # Allocated up front so every frame — including "start" — can carry the
        # id of the row the answer will be stored under. Reused as the primary
        # key when the message is finally inserted.
        assistant_message_id = uuid.uuid4()
        accumulated = ""

        yield _chat_event(
            "start",
            conversation_id=conversation.id,
            message_id=assistant_message_id,
            chunk=None,
            content="",
        )

        try:
            # stream_mode="messages" : chaque token produit par le LLM dans un nœud
            # remonte ici sous la forme (chunk, metadata), sans attendre la fin du graphe.
            async for chunk, _metadata in agent_chat_graph.astream(
                initial_state, stream_mode="messages"
            ):
                # Ce mode réémet aussi les messages écrits dans le state par le nœud
                # (dont la question de l'utilisateur) : on ne garde que les tokens du LLM.
                if not isinstance(chunk, AIMessageChunk):
                    continue

                text = _chunk_text(chunk)
                if not text:
                    continue

                accumulated += text

                yield _chat_event(
                    "token",
                    conversation_id=conversation.id,
                    message_id=assistant_message_id,
                    chunk=text,
                    content=accumulated,
                )

        except asyncio.CancelledError:
            # T3 — the client hung up. Best effort: keep what was already shown
            # on screen, flagged as partial. Dropping it would also leave an
            # orphan question, breaking the user/assistant alternation that
            # _format_history assumes.
            #
            # `except CancelledError` and not `finally`: finally also runs on
            # GeneratorExit, where awaiting is illegal.
            #
            # The shield is mandatory: Starlette runs this inside an anyio task
            # group, whose cancel scope re-delivers the cancellation on every
            # subsequent await — the write would never complete otherwise.
            with anyio.CancelScope(shield=True):
                await self._persist_reply(
                    conversation.id,
                    accumulated,
                    is_partial=True,
                    message_id=assistant_message_id,
                )
            raise

        # No `except Exception: await self.db.rollback()` here, deliberately.
        # An LLM failure unwinds LangGraph's own anyio task group, and touching
        # the request session while that scope is unwinding raises
        # MissingGreenlet — which replaced the real error and escaped past the
        # route, so the client got a broken stream instead of an error frame.
        # Nothing is pending on this session anyway: the question was committed
        # in open_conversation (T1), everything here is a read, and the reply is
        # written through its own session in _persist_reply.

        # T2 — normal end of stream.
        await self._persist_reply(
            conversation.id,
            accumulated,
            is_partial=False,
            message_id=assistant_message_id,
        )

        self.logger.info(
            "Chat reply generated (%d chars)",
            len(accumulated),
            extra={"conversation_id": str(conversation.id)},
        )

        yield _chat_event(
            "complete",
            conversation_id=conversation.id,
            message_id=assistant_message_id,
            chunk=None,
            content=accumulated,
            message=accumulated,
        )

    # -------------------------------------------------------------------------
    # Persistence helper
    # -------------------------------------------------------------------------
    async def _persist_reply(
        self,
        conversation_id: uuid.UUID,
        content: str,
        *,
        is_partial: bool,
        message_id: uuid.UUID | None = None,
    ) -> None:
        """
        Stores the assistant's answer in its OWN session, then commits.

        get_db commits once, after the stream is exhausted — and on client
        disconnect Starlette raises asyncio.CancelledError, which inherits from
        BaseException and therefore escapes get_db's `except Exception`. Nothing
        would be written. A dedicated session also keeps this usable while the
        request session is being torn down.
        """
        if not content:
            return

        try:
            async with AsyncSessionFactory() as session:
                repo = ChatConversationRepository(session)
                await repo.add_message(
                    conversation_id,
                    role="assistant",
                    content=content,
                    is_partial=is_partial,
                    message_id=message_id,
                )
                conversation = await repo.get_by_id(conversation_id)
                if conversation is not None:
                    await repo.touch(conversation, message_delta=1)
                await session.commit()
        except Exception as exc:
            # Never mask a cancellation or an LLM error with a persistence error.
            self.logger.error(
                "Failed to persist assistant reply",
                exc_info=exc,
                extra={
                    "conversation_id": str(conversation_id),
                    "is_partial": is_partial,
                },
            )
