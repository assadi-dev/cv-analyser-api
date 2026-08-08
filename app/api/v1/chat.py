from app.schemas.analyse import ChatMessageAnonymousRequest
import asyncio
import json
import uuid

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.analyse import ChatMessageRequest, ChatResponse
from app.core.exceptions import NotFoundError
from app.services.chat_agent_services import ChatAgentService
from app.core.database import get_db
from app.core.dependencies import get_current_user_id



router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post(
    "/stream-chat-anonymously",
    response_model=str,
    summary="Send a message to the AI assistant on an existing analysis",
)
async def chat_stream_chat_anonymously(
    body: ChatMessageAnonymousRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> str:

   

    service = ChatAgentService(db)
    reply = await service.stream_chat_anonymously(user_id=uuid.UUID(user_id), cv_text=body.cv_text, job_description=body.job_description, message=body.question)

    return "dddd"