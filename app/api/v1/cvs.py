"""
CVs router — upload and manage user resumes.
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user_id
from app.core.exceptions import (
    FileTooLargeError,
    NotFoundError,
    UnsupportedFileTypeError,
)
from app.services.cv_upload_services import CVUploadService
from app.services.cv_service import CVService
from app.core.logging import get_logger
from app.repositories.cv_repo import CVRepository
from app.schemas.common import DeleteResponse, MessageResponse
from app.schemas.cv import CVResponse, CVSetDefaultRequest

logger = get_logger(__name__)
router = APIRouter(prefix="/cvs", tags=["CVs"])
cv_upload_service = CVUploadService()



@router.get(
    "",
    response_model=list[CVResponse],
    summary="List user's CVs",
)
async def list_cvs(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[CVResponse]:
    repo = CVRepository(db)
    cvs = await repo.list_for_user(uuid.UUID(user_id))
    return [CVResponse.model_validate(cv) for cv in cvs]


@router.post(
    "/upload",
    status_code=201,
    summary="Upload a new CV",
)
async def upload_cv(
    file: UploadFile = File(..., description="PDF, DOCX, or TXT resume file"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    cv_service = CVService(db)  
    result = await cv_upload_service.upload_cv(file, user_id)
    cv = await cv_service.create_cv(user_id, result)


    return {"message": "CV uploaded successfully", "key": result.key}


@router.post(
    "/default",
    response_model=MessageResponse,
    summary="Set a CV as the user's default",
)
async def set_default_cv(
    body: CVSetDefaultRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    repo = CVRepository(db)
    cv = await repo.get_by_user_and_id(uuid.UUID(user_id), body.cv_id)
    if cv is None:
        raise NotFoundError(resource="CV", resource_id=str(body.cv_id))

    await repo.set_default(uuid.UUID(user_id), body.cv_id)
    return MessageResponse(message="Default CV updated successfully")


@router.delete(
    "/{cv_id}",
    response_model=DeleteResponse,
    summary="Delete a CV",
)
async def delete_cv(
    cv_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> DeleteResponse:
    repo = CVRepository(db)
    cv = await repo.get_by_user_and_id(uuid.UUID(user_id), cv_id)
    if cv is None:
        raise NotFoundError(resource="CV", resource_id=str(cv_id))

    # Delete physical file
    file_path = Path(cv.file_path)
    if file_path.exists():
        file_path.unlink()

    await repo.delete(cv)
    logger.info("CV deleted", extra={"user_id": user_id, "cv_id": str(cv_id)})
    return DeleteResponse(id=cv_id)
