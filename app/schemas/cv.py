"""CV Pydantic schemas."""

import uuid
from fastapi import File, UploadFile
from pydantic import Field

from app.schemas.common import AppBaseModel, IDSchema, TimestampSchema

class CVUpdateRequest(AppBaseModel):
    """Request to update a CV."""
    name: str | None = None
    is_default: bool | None = None

class CVResponse(IDSchema, TimestampSchema):
    """Full CV metadata response."""
    name: str
    key: str
    file_size_kb: int
    mime_type: str
    is_default: bool



class CVSetDefaultRequest(AppBaseModel):
    """Request to set a CV as the user's default."""
    cv_id: uuid.UUID


class CVExtractRequest(AppBaseModel):
    """Request to extract text from a CV."""
    file: UploadFile = File(..., description="PDF, DOCX, or TXT resume file")

class CVExtractResponse(AppBaseModel):
    """Response after extracting text from a CV."""
    text: str = Field(..., description="Extracted text from the CV")
