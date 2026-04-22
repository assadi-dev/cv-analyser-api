"""CV Pydantic schemas."""

import uuid

from pydantic import Field

from app.schemas.common import AppBaseModel, IDSchema, TimestampSchema


class CVResponse(IDSchema, TimestampSchema):
    """Full CV metadata response."""

    user_id: uuid.UUID
    name: str
    file_size_kb: int
    mime_type: str
    is_default: bool


class CVSetDefaultRequest(AppBaseModel):
    """Request to set a CV as the user's default."""

    cv_id: uuid.UUID
