"""
CVs router — upload and manage user resumes.
"""

from app.services.cv_parser_services import CVParserService
from app.schemas.cv import CVExtractResponse
from app.schemas.cv import CVUpdateRequest
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
    response_model=CVResponse,
    summary="Upload a new CV",
)
async def upload_cv(
    file: UploadFile = File(..., description="PDF, DOCX, or TXT resume file"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
)->CVResponse:
    cv_service = CVService(db)  
    result = await cv_upload_service.upload_cv(file, user_id)
    cv = await cv_service.create_cv(user_id, result)
    logger.info("CV created", extra={"user_id": user_id, "cv_id": str(cv.id)})

    return CVResponse.model_validate(cv)


@router.post(
    "/extract",
    response_model=CVExtractResponse,
    summary="Extract text from a CV",
)
async def extract_cv(
    file: UploadFile = File(..., description="PDF, DOCX, or TXT resume file"),
    user_id: str = Depends(get_current_user_id),
)->CVExtractResponse:

    upload_result = await cv_upload_service.upload_cv(file, user_id)
    text = CVParserService.parse_file(upload_result.file_path)
    if Path(upload_result.file_path).exists():
        Path(upload_result.file_path).unlink()
    return CVExtractResponse(text=text)

@router.put(
    "/{cv_id}",
    response_model=CVResponse,
    summary="Update a CV",
)
async def update_cv(
    cv_id: uuid.UUID,
    body: CVUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),

) -> CVResponse:
    cv_service = CVService(db)
    cv = await cv_service.update_cv(cv_id, body)
    logger.info("CV updated", extra={"user_id": user_id, "cv_id": str(cv_id)})
    return CVResponse.model_validate(cv)


@router.put(
    "/set-default/{cv_id}",
    response_model=MessageResponse,
    summary="Set a CV as the user's default",
)
async def set_default_cv(
    cv_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    cv_service = CVService(db)
    await cv_service.set_default_cv(uuid.UUID(user_id), uuid.UUID(cv_id))
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
    cv_service = CVService(db)
    await cv_service.delete_cv(cv_id)
    return DeleteResponse(message="CV deleted successfully", id=cv_id)


@router.delete(
    "/remove/all",
    response_model=MessageResponse,
    summary="Delete all CVs",
)
async def remove_all_cvs(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    cv_service = CVService(db)
    await cv_service.remove_all_user_cvs(uuid.UUID(user_id))
  
    return MessageResponse(message="All CVs deleted successfully")
    