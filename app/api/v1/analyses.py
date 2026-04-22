"""
Analyses router — AI analysis with SSE streaming.
"""

import json
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user_id
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.repositories.analyse_repo import AnalyseRepository
from app.repositories.candidature_repo import CandidatureRepository
from app.schemas.analyse import AnalyseRequest, AnalyseResponse, ChatMessageRequest, ChatResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/analyses", tags=["Analyses"])


@router.post(
    "/stream",
    summary="Start an AI analysis with SSE real-time streaming",
    description=(
        "Starts the LangGraph analysis pipeline and streams events in real time "
        "using Server-Sent Events (SSE). "
        "Events: progress → result → done (or error on failure)."
    ),
    response_class=StreamingResponse,
)
async def stream_analyse(
    body: AnalyseRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    SSE streaming endpoint for AI analysis.

    The client should open this with an EventSource or fetch + ReadableStream.
    Each event is a JSON-encoded line: data: {...}\\n\\n
    """
    # Verify candidature ownership
    cand_repo = CandidatureRepository(db)
    candidature = await cand_repo.get_by_user_and_id(
        uuid.UUID(user_id), body.candidature_id
    )
    if candidature is None:
        raise NotFoundError(resource="Candidature", resource_id=str(body.candidature_id))

    # Import here to avoid circular imports
    from app.services.analyse_service import AnalyseService

    service = AnalyseService(db)

    async def event_generator():
        try:
            async for event in service.run_stream(
                user_id=uuid.UUID(user_id),
                candidature=candidature,
                request=body,
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as exc:
            logger.error(
                "SSE stream error",
                exc_info=exc,
                extra={"user_id": user_id, "candidature_id": str(body.candidature_id)},
            )
            error_event = {
                "type": "error",
                "message": "Analysis failed. Please try again.",
                "error_code": "ANALYSIS_FAILED",
            }
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        },
    )


@router.get(
    "/{analyse_id}",
    response_model=AnalyseResponse,
    summary="Get a stored analysis result",
)
async def get_analyse(
    analyse_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> AnalyseResponse:
    repo = AnalyseRepository(db)
    analyse = await repo.get_by_user_and_id(uuid.UUID(user_id), analyse_id)
    if analyse is None:
        raise NotFoundError(resource="Analyse", resource_id=str(analyse_id))
    return AnalyseResponse.model_validate(analyse)


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Send a message to the AI assistant on an existing analysis",
)
async def chat(
    body: ChatMessageRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    repo = AnalyseRepository(db)
    analyse = await repo.get_by_user_and_id(uuid.UUID(user_id), body.analyse_id)
    if analyse is None:
        raise NotFoundError(resource="Analyse", resource_id=str(body.analyse_id))

    from app.services.analyse_service import AnalyseService
    service = AnalyseService(db)
    reply = await service.chat(analyse=analyse, message=body.message)

    return ChatResponse(analyse_id=body.analyse_id, message=reply)
