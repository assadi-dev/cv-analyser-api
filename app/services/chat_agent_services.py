from app.agents.agent_chat import AgentChatState
from app.core.config import settings
from app.repositories.preference_repo import PreferenceRepository
from app.models import Preference
import uuid
from collections.abc import AsyncGenerator
from typing import Any
from app.core.logging import get_logger
from app.services.provider_service import ProviderService
from app.agents.agent_chat import agent_chat_graph

from sqlalchemy.ext.asyncio import AsyncSession



logger = get_logger(__name__)

class ChatAgentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = get_logger(__name__)
    
    async def stream_chat_anonymously(self, user_id: uuid.UUID, cv_text: str, job_description: str, message: str) -> str:
         # ---------------------------------------------------------------
        # Step 2 — Resolve AI provider config
        # ---------------------------------------------------------------
        preference_repo = PreferenceRepository(self.db)
        preference = await preference_repo.get_by_user_id(user_id)

        api_key = ""
        if preference.ai_api_key_encrypted:
            api_key = ProviderService.decrypt_api_key(preference.ai_api_key_encrypted)

        preference = await preference_repo.get_by_user_id(user_id)
        
        if preference is None:
            return "No preference found"


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
        
        graph_invoke = agent_chat_graph.invoke(initialState)
        
      
        print(graph_invoke["messages"][-1].content)
        
        return "hello"