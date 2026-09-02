"""Candidature and Contact Pydantic schemas."""

import uuid
from typing import Literal

from pydantic import Field, HttpUrl, field_validator

from app.schemas.common import AppBaseModel, IDSchema, TimestampSchema

# ---------------------------------------------------------------------------
# Contact schemas
# ---------------------------------------------------------------------------

ContactType = Literal["email", "phone"]
ContractType = Literal["CDI", "CDD", "Freelance", "Stage", "Alternance"]
WorkMode = Literal["remote", "hybrid", "on-site"]
CandidatureStatus = Literal["to_send", "sent", "interview", "rejected", "accepted"]


class ContactCreate(AppBaseModel):
    """Schema for creating a contact linked to a candidature."""

    name: str = Field(..., min_length=1, max_length=255)
    contact_type: ContactType = Field(default="email")
    value: str = Field(..., min_length=1, max_length=255)


class ContactResponse(IDSchema, TimestampSchema):
    """Full contact response schema."""

    candidature_id: uuid.UUID
    name: str
    contact_type: ContactType
    value: str


# ---------------------------------------------------------------------------
# Candidature schemas
# ---------------------------------------------------------------------------

class CandidatureCreate(AppBaseModel):
    """Schema for creating a new candidature."""

    # Company & position
    company_name: str = Field(..., min_length=1, max_length=255)
    company_city: str | None = Field(default=None, max_length=100)
    company_region: str | None = Field(default=None, max_length=100)
    company_country: str | None = Field(default=None, max_length=100)
    job_title: str = Field(..., min_length=1, max_length=255)
    contract_type: ContractType = Field(default="CDI")
    work_mode: WorkMode = Field(default="hybrid")

    # Source
    source_platform: str | None = Field(default=None, max_length=100)
    source_name: str | None = Field(default=None, max_length=255)
    source_url: str | None = Field(default=None)

    # Application data
    cv_id: uuid.UUID | None = Field(default=None)
    job_description: str | None = Field(
        default=None,
        description="Job offer text — triggers AI analysis if provided",
    )
    status: CandidatureStatus = Field(default="to_send")
    notes: str | None = Field(default=None)

    # Contacts
    contacts: list[ContactCreate] = Field(default_factory=list)

    @field_validator("source_url")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        """Loosely validate URL format."""
        if v and not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("source_url must be a valid HTTP/HTTPS URL")
        return v


class CandidatureUpdate(AppBaseModel):
    """Schema for partially updating a candidature (all fields optional)."""

    company_name: str | None = Field(default=None, max_length=255)
    company_city: str | None = Field(default=None, max_length=100)
    job_title: str | None = Field(default=None, max_length=255)
    contract_type: ContractType | None = None
    work_mode: WorkMode | None = None
    source_platform: str | None = Field(default=None, max_length=100)
    source_name: str | None = Field(default=None, max_length=255)
    source_url: str | None = None
    cv_id: uuid.UUID | None = None
    status: CandidatureStatus | None = None
    notes: str | None = None


class CandidatureStatusUpdate(AppBaseModel):
    """Schema for updating only the status (Kanban drag & drop)."""

    status: CandidatureStatus


class CandidatureStatusResponse(AppBaseModel):
    """Schema for updating only the status (Kanban drag & drop)."""
    id: uuid.UUID
    status: CandidatureStatus


class CandidatureMove(AppBaseModel):
    """
    Schema for moving a card on the board (Kanban drag & drop).

    Carries the neighbours framing the drop point rather than a position: the
    board only knows the ids it renders, and the backend reads their live
    positions. A stale client cache therefore cannot write a wrong rank.

    `after_id` is the primary anchor — the card takes its position and pushes
    it down. `before_id` only matters when dropping at the end of a column,
    where there is no card after. Both null means an empty column.
    """

    status: CandidatureStatus
    before_id: uuid.UUID | None = Field(
        default=None, description="Candidature id of the card above the drop point"
    )
    after_id: uuid.UUID | None = Field(
        default=None, description="Candidature id of the card below the drop point"
    )


class CandidatureMoveResponse(AppBaseModel):
    """
    Result of a board move: the placement the backend actually applied.

    `status` is a plain `str`, matching CandidatureResponse and
    CandidatureSummary — strict on the way in, permissive on the way out.
    Returning both fields lets the board reconcile its optimistic update
    without a refetch.
    """

    message: str = "candidature position has been updated"
    status: str
    position: int

class CandidatureResponse(IDSchema, TimestampSchema):
    """Full candidature response with nested contacts."""

    id: uuid.UUID
    cv_id: uuid.UUID | None
    analyse_id: uuid.UUID | None = None
    company_name: str
    company_city: str | None
    company_region: str | None
    company_country: str | None
    job_title: str
    contract_type: str
    work_mode: str
    source_platform: str | None
    source_url: str | None
    status: str
    notes: str | None
    #contacts: list[ContactResponse] = Field(default_factory=list)


class CandidatureSummary(IDSchema, TimestampSchema):
    """Lightweight candidature schema for list views (no contacts)."""

    company_name: str
    job_title: str
    status: str
    contract_type: str
    work_mode: str
    source_platform: str | None
    source_url: str | None
    company_city: str | None
    company_region: str | None
    company_country: str | None
    notes: str | None
    #contacts: list[ContactResponse] = Field(default_factory=list)
