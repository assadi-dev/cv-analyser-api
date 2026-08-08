"""Analyse Pydantic schemas."""

import uuid
from typing import Any, Literal

from pydantic import Field

from app.schemas.common import AppBaseModel, IDSchema, TimestampSchema

# ---------------------------------------------------------------------------
# SSE event schemas (streaming)
# ---------------------------------------------------------------------------

SSEEventType = Literal["progress", "result", "error", "done"]
AnalyseStep = Literal["parsing", "ats", "scoring", "recommendations"]


class SSEProgressEvent(AppBaseModel):
    """Emitted during each agent node execution."""

    type: Literal["progress"] = "progress"
    step: AnalyseStep
    progress: int = Field(ge=0, le=100, description="Overall progress percentage")
    data: dict[str, Any] = Field(default_factory=dict)


class SSEResultEvent(AppBaseModel):
    """Emitted when the full analysis is complete."""

    type: Literal["result"] = "result"
    score_global: int
    score_ats: int
    score_competences: int
    score_experience: int
    keywords_found: list[str]
    keywords_missing: list[str]
    recommandations: list[dict[str, Any]]


class SSEErrorEvent(AppBaseModel):
    """Emitted if the agent encounters a fatal error."""

    type: Literal["error"] = "error"
    message: str
    error_code: str


class SSEDoneEvent(AppBaseModel):
    """Emitted as the final event to close the SSE stream."""

    type: Literal["done"] = "done"
    analyse_id: uuid.UUID


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class AnalyseRequest(AppBaseModel):
    """Request body to start an AI analysis."""

    candidature_id: uuid.UUID = Field(description="Candidature to attach this analysis to")
    cv_id: uuid.UUID | None = Field(
        default=None,
        description="CV to use — falls back to user's default CV",
    )
    job_description: str = Field(
        ...,
        description="Raw job offer text",
    )
    cv_text: str | None = Field(
        default=None,
        description="Pre-extracted CV text — if None, the stored CV file is parsed",
    )

class AnalyseRequestTemporary(AppBaseModel):
    """Request body to start an AI analysis (no auth required)."""
    cv_text: str = Field(
        ...,
        description="CV text to analyse",
    )
    job_description: str = Field(
        ...,
        description="Raw job offer text",
    )


# Chat schemas live in app/schemas/chat.py — conversations are now persisted
# in their own tables rather than in the analyses.chat_history JSON column.


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class RecommandationItem(AppBaseModel):
    """A single AI recommendation."""

    type: Literal["warning", "success", "info"]
    title: str
    description: str
    impact: Literal["high", "medium", "low"] = "medium"


class AnalyseResponse(IDSchema, TimestampSchema):
    """Full analysis result."""

    candidature_id: uuid.UUID
    cv_id: uuid.UUID | None
    score_global: int
    score_ats: int
    score_competences: int
    score_experience: int
    keywords_found: list[str]
    keywords_missing: list[str]
    recommandations: list[dict[str, Any]]
    chat_history: list[dict[str, Any]]
    ai_provider: str
    ai_model: str
