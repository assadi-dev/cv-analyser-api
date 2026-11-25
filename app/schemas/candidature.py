"""Candidature and Contact Pydantic schemas."""

import uuid
from typing import Annotated, Literal

from pydantic import Field, HttpUrl, StringConstraints, field_validator

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
    # Required: the offer text is what an analysis of this candidature runs on,
    # so one without it could never be pre-filled. Whitespace-only counts as
    # missing. (Editing keeps it optional — see CandidatureUpdate.)
    job_description: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] = Field(
        ...,
        description="Job offer text, kept on the candidature and used to pre-fill analyses",
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
    job_description: str | None = None
    status: CandidatureStatus | None = None
    notes: str | None = None
    contacts: list[ContactCreate] | None = Field(
        default=None,
        description=(
            "Replaces the whole contact list when given. Omit it to leave the "
            "contacts untouched; an empty list removes them all."
        ),
    )


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
    # Only here, not on the list summary: the text can be long and the list
    # never shows it.
    job_description: str | None = None
    #contacts: list[ContactResponse] = Field(default_factory=list)


class CandidatureDetail(CandidatureResponse):
    """
    One candidature read in full, contacts included.

    Kept apart from CandidatureResponse on purpose: the write endpoints build
    that one from a row whose contacts are not loaded, and reading them there
    would trigger a lazy load outside the async session.
    """

    contacts: list[ContactResponse] = Field(default_factory=list)


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


class KanbanBoardResponse(AppBaseModel):
    """
    The board, ready to render: one entry per column, cards already ordered.

    Shaped as `{status: [cards]}` because that is what the board component
    consumes directly — the client groups nothing and sorts nothing.

    Every known column is always present, empty ones included. Omitting them
    would make a column disappear from the board as soon as its last card
    leaves, and there would be nowhere left to drop a card back into.
    """

    columns: dict[str, list[CandidatureSummary]]
