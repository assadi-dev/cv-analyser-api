"""CV Pydantic schemas."""

import uuid

from pydantic import Field

from app.schemas.common import AppBaseModel, IDSchema, TimestampSchema

class CVUpdateRequest(AppBaseModel):
    """Request to update a CV."""
    name: str | None = None
    is_default: bool | None = None

class CVResponse(IDSchema, TimestampSchema):
    """Full CV metadata response."""
    name: str
    file_size_kb: int
    mime_type: str
    is_default: bool


class CVSetDefaultRequest(AppBaseModel):
    """Request to set a CV as the user's default."""
    cv_id: uuid.UUID
