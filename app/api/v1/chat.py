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
from app.core.logging import get_logger


logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post(
    "/stream-chat-anonymously",
    response_class=StreamingResponse,
    summary="Send a message to the AI assistant and stream the answer (SSE)",
    description=(
        "Runs the chat agent and streams the answer token by token using "
        "Server-Sent Events (SSE). Events: start → token* → complete (or error)."
    ),
)
async def chat_stream_chat_anonymously(
    body: ChatMessageAnonymousRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    SSE streaming endpoint for the anonymous chat.

    Each frame is a JSON-encoded line: data: {...}\\n\\n
    """
    service = ChatAgentService(db)

    async def event_generator():
        try:
            async for event in service.stream_chat_anonymously(
                user_id=uuid.UUID(user_id),
                cv_text=body.cv_text,
                job_description=body.job_description,
                message=body.question,
            ):
                # ensure_ascii=False : sinon json.dumps échappe les accents
                # en séquences \\uXXXX dans les frames SSE.
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            logger.info("Client déconnecté", extra={"user_id": user_id})
            raise
        except Exception as exc:
            logger.error(
                "SSE chat stream error",
                exc_info=exc,
                extra={"user_id": user_id},
            )
            error_event = {
                "type": "error",
                "message": "Chat failed. Please try again.",
                "error_code": "CHAT_FAILED",
            }
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        },
    )