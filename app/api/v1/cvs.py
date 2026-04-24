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
from app.core.logging import get_logger
from app.repositories.cv_repo import CVRepository
from app.schemas.common import DeleteResponse, MessageResponse
from app.schemas.cv import CVResponse, CVSetDefaultRequest

logger = get_logger(__name__)
router = APIRouter(prefix="/cvs", tags=["CVs"])

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


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
    "",

    status_code=201,
    summary="Upload a new CV",
)
async def upload_cv(
    file: UploadFile = File(..., description="PDF, DOCX, or TXT resume file"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    # Validate file extension
    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise UnsupportedFileTypeError(
            detail=f"Unsupported file type '{extension}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Read and validate file size
    content = await file.read()
    size_bytes = len(content)
    if size_bytes > settings.max_cv_size_bytes:
        print(settings.max_cv_size_mb)
        raise FileTooLargeError(
            detail=f"File size {size_bytes // 1024} KB exceeds maximum of {settings.max_cv_size_mb} MB"
        )

    # Save file to disk
    upload_path = Path(settings.upload_dir) / user_id/settings.cv_dir
    upload_path.mkdir(parents=True, exist_ok=True)

    filename = file.filename
    uuid_file = str(uuid.uuid4().hex)
    key = f"{uuid_file}{extension}"
    file_path = upload_path / key
    file_path.write_bytes(content)

    # Persist metadata
    """     repo = CVRepository(db)
    cv = await repo.create(
        user_id=uuid.UUID(user_id),
        name=file.filename or filename,
        file_path=str(file_path),
        file_size_kb=size_bytes // 1024,
        mime_type=file.content_type or "application/octet-stream",
        is_default=False,
    )
 """
    # Auto-set as default if it's the first CV
    """     existing = await repo.list_for_user(uuid.UUID(user_id))
    if len(existing) == 1:
        await repo.set_default(uuid.UUID(user_id), cv.id)
        cv.is_default = True

    logger.info(
        "CV uploaded",
        extra={
            "user_id": user_id,
            "cv_id": str(cv.id),
            "filename": file.filename,
            "size_kb": cv.file_size_kb,
        },
    ) """
    return {"message": "CV uploaded successfully", "key": key, "filename": filename, "extension": extension, "mime_type": file.content_type, "file_size_kb": size_bytes // 1024}


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
