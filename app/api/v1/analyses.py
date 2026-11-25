"""
Analyses router — AI analysis with SSE streaming.
"""

from app.models.candidature import Candidature
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
from app.core.exceptions import (
    CVTextUnreadableError,
    InternalError,
    NotFoundError,
    UnprocessableError,
)
from app.core.logging import get_logger
from app.repositories.analyse_repo import AnalyseRepository
from app.repositories.candidature_repo import CandidatureRepository
from app.schemas.analyse import AnalyseRequest, AnalyseResponse

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
    # Verify candidature ownership — only when one is attached. Without it the
    # analysis is standalone, and ownership rests on Analyse.user_id.
    candidature = None
    if body.candidature_id is not None:
        cand_repo = CandidatureRepository(db)
        candidature = await cand_repo.get_by_user_and_id(
            uuid.UUID(user_id), body.candidature_id
        )
        if candidature is None:
            raise NotFoundError(
                resource="Candidature", resource_id=str(body.candidature_id)
            )

    service = AnalyseService(db)

    async def event_generator():
        try:
            async for event in service.run_stream_candidature(
                user_id=uuid.UUID(user_id),
                candidature=candidature,
                request=body,
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as exc:
            logger.error(
                "SSE stream error",
                exc_info=exc,
                extra={
                    "user_id": user_id,
                    "candidature_id": str(body.candidature_id)
                    if body.candidature_id
                    else None,
                },
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





# Sentinel pushed on the queue once the producer task is over. An explicit
# end-of-stream marker is what lets the consumer drain everything already
# queued: polling Task.done() instead would stop the loop while the last
# events are still sitting in the queue.
_STREAM_END = object()


async def analyse_temporary_task(
    queue: asyncio.Queue,
    db: AsyncSession,
    user_id: uuid.UUID,
    request: AnalyseRequestTemporary,
    candidature: Candidature | None = None,
    cv_id: uuid.UUID | None = None,
) -> None:
    """
    Runs the analysis pipeline and pushes each SSE frame onto the queue.

    With a `candidature`, the analysis is recorded on it (and replaces the one
    it pointed at before). Without, it stays standalone. `cv_id` is the stored
    CV the text came from, recorded on the analysis; it only applies with a
    candidature, the standalone pipeline does not keep one.
    """
    service = AnalyseService(db)
    try:
        if candidature is None:
            events = service.run_stream_anonymous(user_id=user_id, request=request)
        else:
            events = service.run_stream_candidature(
                user_id=user_id,
                candidature=candidature,
                request=AnalyseRequest(
                    candidature_id=candidature.id,
                    cv_id=cv_id,
                    cv_text=request.cv_text,
                    job_description=request.job_description,
                ),
            )
        async for event in events:
            # ensure_ascii=False : sinon json.dumps échappe les accents des
            # recommandations en séquences \uXXXX dans les frames SSE.
            await queue.put(f"data: {json.dumps(event, ensure_ascii=False)}\n\n")
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
    finally:
        # Always signal the end, including on error — otherwise the consumer
        # would wait on queue.get() forever.
        await queue.put(_STREAM_END)


@router.post(
    "/temporary/stream",
    response_class=StreamingResponse,
    summary="Start a temporary AI analysis with SSE real-time streaming",
)
async def stream_analyse_temporary(
    job_description: Annotated[str, Form(min_length=10, description="Raw job offer text")],
    cv_file: Annotated[
        UploadFile | None,
        File(description="CV file to analyse — omit to use a stored CV through `cv_id`"),
    ] = None,
    cv_id: Annotated[
        uuid.UUID | None,
        Form(description="One of the user's stored CVs, used when no file is sent"),
    ] = None,
    candidature_id: Annotated[
        uuid.UUID | None,
        Form(description="Candidature to attach the analysis to — omit for a standalone one"),
    ] = None,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    SSE streaming endpoint for temporary users.

    Expects multipart/form-data — `job_description` as a text field and
    `cv_file` as a file upload. Sending a JSON body yields a 422.

    The CV comes either from `cv_file` (read and thrown away, as before) or
    from `cv_id`, one of the user's stored CVs whose text was kept at upload.
    A file wins when both are sent.

    `candidature_id` is optional. When given, the user must own that
    candidature, and the resulting analysis is attached to it.
    """
    if cv_file is None and cv_id is None:
        raise UnprocessableError(detail="Send a CV file, or the id of one of your CVs.")

    # Resolved before streaming starts: once the response is open, a 404 can no
    # longer be reported as a status code.
    candidature = None
    if candidature_id is not None:
        candidature = await CandidatureRepository(db).get_by_user_and_id(
            uuid.UUID(user_id), candidature_id
        )
        if candidature is None:
            raise NotFoundError(
                resource="Candidature", resource_id=str(candidature_id)
            )

    cv_service = CVService(db)
    if cv_file is not None:
        try:
            cv_text = await cv_service.extract_cv_text(cv_file, user_id)
        except InternalError as exc:
            # A supported file that cannot be parsed (corrupted, protected):
            # the CV is at fault, not the server.
            raise CVTextUnreadableError(
                detail="The CV file could not be read.",
                context={"filename": cv_file.filename},
            ) from exc
        stored_cv_id = None
    else:
        # `cv_id` is not None here: the guard above rejected neither being sent.
        cv_text = await cv_service.resolve_text(uuid.UUID(user_id), cv_id)  # type: ignore[arg-type]
        stored_cv_id = cv_id
 

    if not cv_text or not cv_text.strip():
        raise CVTextUnreadableError(
            detail="No text could be extracted from the CV file.",
            context={"filename": cv_file.filename if cv_file else None, "cv_id": str(cv_id) if cv_id else None},
        )


    async def event_generator():
        queue = asyncio.Queue()
        analyse_task = None
        try:
            analyse_request = AnalyseRequestTemporary(
                cv_text=cv_text,
                job_description=job_description,
            )
            analyse_task = asyncio.create_task(
                analyse_temporary_task(
                    queue, db, uuid.UUID(user_id), analyse_request, candidature, stored_cv_id
                )
            )
            while True:
                frame = await queue.get()
                if frame is _STREAM_END:
                    break
                yield frame
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
