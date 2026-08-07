"""
Analyses router — AI analysis with SSE streaming.
"""

from app.schemas.analyse import AnalyseRequestTemporary
from app.services.analyse_service import AnalyseService
from app.services.cv_service import CVService
import asyncio
import json
import uuid

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user_id
from app.core.exceptions import NotFoundError, UnprocessableError
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


async def analyse_temporary_task(queue: asyncio.Queue,db, user_id:uuid.UUID, request:AnalyseRequestTemporary):

    service = AnalyseService(db)
    try:
        async for event in service.run_stream_anonymous(user_id = user_id,request = request):
            await queue.put(f"data: {json.dumps(event)}\n\n")
    except Exception as exc:
        logger.error(
            "SSE stream error",
            exc_info=exc,
            extra={"user_id": user_id},
        )
        error_event = {
            "type": "error",
            "message": "Analysis failed. Please try again.",
            "error_code": "ANALYSIS_FAILED",
        }
        await queue.put(f"data: {json.dumps(error_event)}\n\n")


 
    await queue.put("data: done\n\n")
       


@router.post(
    "/temporary/stream",
    response_class=StreamingResponse,
    summary="Start a temporary AI analysis with SSE real-time streaming",
)
async def stream_analyse_temporary(
    job_description: Annotated[str, Form(min_length=10, description="Raw job offer text")],
    cv_file: Annotated[UploadFile, File(description="CV file to analyse")],
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    SSE streaming endpoint for temporary users.

    Expects multipart/form-data — `job_description` as a text field and
    `cv_file` as a file upload. Sending a JSON body yields a 422.
    """
    cv_service = CVService(db)
    cv_text = await cv_service.extract_cv_text(cv_file, user_id)

    if not cv_text or not cv_text.strip():
        raise UnprocessableError(
            detail="No text could be extracted from the CV file.",
            context={"filename": cv_file.filename},
        )


    async def event_generator():
        queue = asyncio.Queue()
        analyse_task = None
        try:
            analyse_request = AnalyseRequestTemporary(
                cv_text=cv_text,
                job_description=job_description,
            )
            analyse_task = asyncio.create_task(analyse_temporary_task(queue, db, uuid.UUID(user_id), analyse_request))
            while not analyse_task.done():
                yield await queue.get()
        except asyncio.CancelledError:
            logger.info("Client déconnecté")
        except Exception as exc:
            logger.error(
                "SSE stream error",
                exc_info=exc,
                extra={"user_id": user_id},
            )
            error_event = {
                "type": "error",
                "message": "Analysis failed. Please try again.",
                "error_code": "ANALYSIS_FAILED",
            }
            yield f"data: {json.dumps(error_event)}\n\n"
        finally:
           if analyse_task:
                analyse_task.cancel()
                try:
                    await analyse_task
                except asyncio.CancelledError:
                    pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        },
    )
