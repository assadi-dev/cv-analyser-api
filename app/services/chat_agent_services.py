from app.agents.agent_chat import AgentChatState
from app.core.config import settings
from app.repositories.preference_repo import PreferenceRepository
from app.models import Preference
import uuid
from collections.abc import AsyncGenerator
from typing import Any
from langchain_core.messages import AIMessageChunk

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.services.provider_service import ProviderService
from app.agents.agent_chat import agent_chat_graph

from sqlalchemy.ext.asyncio import AsyncSession



logger = get_logger(__name__)


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


class ChatAgentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = get_logger(__name__)
    
    async def stream_chat_anonymously(
        self,
        user_id: uuid.UUID,
        cv_text: str,
        job_description: str,
        message: str,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Exécute le graphe de chat et émet les événements SSE au fil de l'eau.

        Chaque événement porte les mêmes 3 propriétés :
          - chunk    : le fragment reçu à cet instant
          - message  : la concaténation des chunks précédents (sans celui-ci)
          - complete : le message complet à cet instant (message + chunk)

        Types d'événements : start → token* → complete.
        Sur "complete" (fin du stream LLM), chunk est vide et
        message == complete == réponse finale.
        """
         # ---------------------------------------------------------------
        # Step 2 — Resolve AI provider config
        # ---------------------------------------------------------------
        preference_repo = PreferenceRepository(self.db)
        preference = await preference_repo.get_by_user_id(user_id)

        if preference is None:
            raise NotFoundError(resource="Preference", resource_id=str(user_id))

        api_key = ""
        if preference.ai_api_key_encrypted:
            api_key = ProviderService.decrypt_api_key(preference.ai_api_key_encrypted)

        initialState = AgentChatState(
            language = "fr",
            provider = preference.ai_provider,
            model = preference.ai_model,
            api_key = api_key,
            recommendations = "test",
            score = "70",
            job_description = job_description,
            cv = cv_text,
            messages = [],
            user_message = message,
        )
        # Ne jamais logger initialState tel quel : il contient la clé API en clair.
        self.logger.info(
            "Chat stream started",
            extra={
                "user_id": str(user_id),
                "provider": preference.ai_provider,
                "model": preference.ai_model,
            },
        )

        yield {"type": "start", "chunk": "", "message": "", "complete": ""}

        accumulated = ""

        # stream_mode="messages" : chaque token produit par le LLM dans un nœud
        # remonte ici sous la forme (chunk, metadata), sans attendre la fin du graphe.
        async for chunk, _metadata in agent_chat_graph.astream(
            initialState, stream_mode="messages"
        ):
            # Ce mode réémet aussi les messages écrits dans le state par le nœud
            # (dont la question de l'utilisateur) : on ne garde que les tokens du LLM.
            if not isinstance(chunk, AIMessageChunk):
                continue

            text = _chunk_text(chunk)
            if not text:
                continue

            previous = accumulated
            accumulated += text

            yield {
                "type": "token",
                "chunk": text,
                "message": previous,
                "complete": accumulated,
            }

        self.logger.info("Chat reply generated (%d chars)", len(accumulated))

        yield {
            "type": "complete",
            "chunk": "",
            "message": accumulated,
            "complete": accumulated,
        }