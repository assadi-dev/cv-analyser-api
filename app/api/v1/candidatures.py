"""
Candidatures router — full CRUD for job applications.
"""

from app.schemas.common import MessageResponse
from app.services.candidature_services import CandidatureService
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_current_user_id
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.repositories.candidature_repo import CandidatureRepository
from app.repositories.contact_repo import ContactRepository
from app.schemas.candidature import (
    CandidatureCreate,
    CandidatureResponse,
    CandidatureStatusUpdate,
    CandidatureSummary,
    CandidatureUpdate,
)
from app.schemas.common import DeleteResponse, PaginatedResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/candidatures", tags=["Candidatures"])


@router.get(
    "",
    response_model=PaginatedResponse[CandidatureSummary],
    summary="List user's candidatures",
)
async def list_candidatures(
    status: str | None = Query(default=None, description="Filter by status"),
    pagination: PaginationParams = Depends(),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[CandidatureSummary]:
    repo = CandidatureRepository(db)
    items, total = await repo.list_for_user(
        uuid.UUID(user_id),  
        status=status,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    return PaginatedResponse.build(
        items=[CandidatureSummary.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post(
    "",
    response_model=CandidatureResponse,
    status_code=201,
    summary="Create a new candidature",
)
async def create_candidature(
    body: CandidatureCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> CandidatureResponse:
    candidature_service = CandidatureService(db)
    candidature = await candidature_service.create_candidature(body, uuid.UUID(user_id))

    return CandidatureResponse.model_validate(candidature)


@router.get(
    "/{candidature_id}",
    response_model=CandidatureResponse,
    summary="Get a candidature by ID",
)
async def get_candidature(
    candidature_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> CandidatureResponse:
    repo = CandidatureRepository(db)
    candidature = await repo.get_by_user_and_id(
        uuid.UUID(user_id), candidature_id
    )
    if candidature is None:
        raise NotFoundError(resource="Candidature", resource_id=str(candidature_id))
    return CandidatureResponse.model_validate(candidature)


@router.patch(
    "/{candidature_id}",
    response_model=CandidatureResponse,
    summary="Partially update a candidature",
)
async def update_candidature(
    candidature_id: uuid.UUID,
    body: CandidatureUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> CandidatureResponse:
    repo = CandidatureRepository(db)
    candidature = await repo.get_by_user_and_id(uuid.UUID(user_id), candidature_id)
    if candidature is None:
        raise NotFoundError(resource="Candidature", resource_id=str(candidature_id))

    updated = await repo.update(
        candidature,
        **body.model_dump(exclude_none=True),
    )
    return CandidatureResponse.model_validate(updated)


@router.patch(
    "/{candidature_id}/status",
    response_model=CandidatureResponse,
    summary="Update candidature status (Kanban drag & drop)",
)
async def update_status(
    candidature_id: uuid.UUID,
    body: CandidatureStatusUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> CandidatureResponse:
    repo = CandidatureRepository(db)
    candidature = await repo.get_by_user_and_id(uuid.UUID(user_id), candidature_id)
    if candidature is None:
        raise NotFoundError(resource="Candidature", resource_id=str(candidature_id))

    updated = await repo.update(candidature, status=body.status)

    logger.info(
        "Candidature status updated",
        extra={
            "user_id": user_id,
            "candidature_id": str(candidature_id),
            "new_status": body.status,
        },
    )
    return CandidatureResponse.model_validate(updated)


@router.delete(
    "/{candidature_id}",
    response_model=DeleteResponse,
    summary="Delete a candidature",
)
async def delete_candidature(
    candidature_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> DeleteResponse:
    repo = CandidatureRepository(db)
    candidature = await repo.get_by_user_and_id(uuid.UUID(user_id), candidature_id)
    if candidature is None:
        raise NotFoundError(resource="Candidature", resource_id=str(candidature_id))

    await repo.delete(candidature)
    logger.info(
        "Candidature deleted",
        extra={"user_id": user_id, "candidature_id": str(candidature_id)},
    )
    return DeleteResponse(id=candidature_id)


@router.delete(
    "/remove/all",
    response_model=MessageResponse,
    summary="Delete all user's candidatures",
)
async def delete_all_user_candidature(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    repo = CandidatureRepository(db)
    await repo.delete_all_user_candidature(uuid.UUID(user_id))
    return MessageResponse(message="All user's candidatures deleted")