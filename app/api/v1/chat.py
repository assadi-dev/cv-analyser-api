"""
Chat router — streaming conversation with the AI assistant, persisted.
"""

import asyncio
import json
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_current_user_id
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.repositories.chat_conversation_repo import ChatConversationRepository
from app.schemas.chat import (
    ChatConversationDetail,
    ChatConversationUpdate,
    ChatMessageResponse,
    ChatStreamRequest,
)
from app.schemas.common import DeleteResponse, PaginatedResponse
from app.services.chat_agent_services import ChatAgentService

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post(
    "/stream-chat-anonymously",
    response_class=StreamingResponse,
    summary="Send a message to the AI assistant and stream the answer (SSE)",
    description=(
        "Runs the chat agent and streams the answer token by token using "
        "Server-Sent Events (SSE). Events: start → token* → complete (or error). "
        "Every event carries the conversation_id; pass it back to resume the thread."
    ),
)
async def chat_stream(
    body: ChatStreamRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    SSE streaming endpoint for the chat.

    Each frame is a JSON-encoded line: data: {...}\\n\\n
    """
    service = ChatAgentService(db)

    # Resolved BEFORE the StreamingResponse: an unknown or foreign
    # conversation_id must be a real HTTP 404, not an SSE error frame sent
    # after a 200 has already gone out. It is also what makes the id available
    # for the response header.
    conversation, user_seq = await service.open_conversation(uuid.UUID(user_id), body)

    async def event_generator():
        try:
            async for event in service.stream_chat(conversation, body.question, user_seq):
                # ensure_ascii=False : sinon json.dumps échappe les accents
                # en séquences \\uXXXX dans les frames SSE.
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            logger.info(
                "Client déconnecté",
                extra={"user_id": user_id, "conversation_id": str(conversation.id)},
            )
            raise
        except Exception as exc:
            logger.error(
                "SSE chat stream error",
                exc_info=exc,
                extra={"user_id": user_id, "conversation_id": str(conversation.id)},
            )
            error_event = {
                "type": "error",
                "message": "Chat failed. Please try again.",
                "error_code": "CHAT_FAILED",
                "conversation_id": str(conversation.id),
            }
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
            "X-Conversation-Id": str(conversation.id),
        },
    )


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=PaginatedResponse[ChatMessageResponse],
    summary="Replay a conversation",
)
async def list_conversation_messages(
    conversation_id: uuid.UUID,
    pagination: PaginationParams = Depends(),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ChatMessageResponse]:
    repo = ChatConversationRepository(db)

    conversation = await repo.get_for_user(conversation_id, uuid.UUID(user_id))
    if conversation is None:
        raise NotFoundError(
            resource="ChatConversation", resource_id=str(conversation_id)
        )

    items, total = await repo.list_messages(
        conversation_id, offset=pagination.offset, limit=pagination.limit
    )
    return PaginatedResponse.build(
        items=[ChatMessageResponse.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.patch(
    "/conversations/{conversation_id}",
    response_model=ChatConversationDetail,
    summary="Rename or archive a conversation",
)
async def update_conversation(
    conversation_id: uuid.UUID,
    body: ChatConversationUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ChatConversationDetail:
    repo = ChatConversationRepository(db)

    conversation = await repo.get_for_user(conversation_id, uuid.UUID(user_id))
    if conversation is None:
        raise NotFoundError(
            resource="ChatConversation", resource_id=str(conversation_id)
        )

    updated = await repo.apply_update(
        conversation, title=body.title, is_archived=body.is_archived
    )
    return ChatConversationDetail.model_validate(updated)


@router.delete(
    "/conversations/{conversation_id}",
    response_model=DeleteResponse,
    summary="Delete a conversation and all its messages",
)
async def delete_conversation(
    conversation_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> DeleteResponse:
    repo = ChatConversationRepository(db)

    conversation = await repo.get_for_user(conversation_id, uuid.UUID(user_id))
    if conversation is None:
        raise NotFoundError(
            resource="ChatConversation", resource_id=str(conversation_id)
        )

    # Messages go with it: FK ON DELETE CASCADE + ORM delete-orphan.
    await repo.delete(conversation)
    return DeleteResponse(id=conversation_id)
