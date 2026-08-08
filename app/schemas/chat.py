"""
Pydantic schemas for the persistent chat conversations.

The analysis context (CV, job offer, score, recommendations) is sent once, with
the first question, and snapshotted on the conversation. Resuming only requires
`conversation_id` + `question`.
"""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from app.schemas.common import AppBaseModel, IDSchema, TimestampSchema

# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class ChatStreamRequest(AppBaseModel):
    """
    Body of the streaming chat endpoint.

    Two modes:
      - new conversation:  cv_text + job_description (+ optional score /
        recommandations / analyse_id) and no conversation_id;
      - resume:            conversation_id + question only. Any context sent
        alongside is ignored — the stored snapshot wins.
    """

    conversation_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "Resume an existing conversation. When set, the analysis context "
            "in this body is ignored: the stored snapshot is authoritative."
        ),
    )
    analyse_id: uuid.UUID | None = Field(
        default=None,
        description="Link the conversation to a persisted analysis, when there is one.",
    )

    question: str = Field(..., min_length=1, max_length=4000, description="Question from user")

    # --- Analysis context, first message only --------------------------------
    cv_text: str | None = Field(default=None, description="CV text the assistant reasons on")
    job_description: str | None = Field(default=None, description="Raw job offer text")
    score_global: int | None = Field(
        default=None, ge=0, le=100, description="Match score (0-100)"
    )
    recommandations: list[dict[str, Any]] | None = Field(
        default=None, description="Recommendations produced by the analysis"
    )

    @model_validator(mode="after")
    def _require_context_on_first_message(self) -> "ChatStreamRequest":
        if self.conversation_id is None and not (self.cv_text and self.job_description):
            raise ValueError(
                "cv_text and job_description are required when starting a new conversation"
            )
        return self


class ChatConversationUpdate(AppBaseModel):
    """PATCH body — rename and/or archive a conversation."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    is_archived: bool | None = None


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class ChatMessageResponse(IDSchema):
    """One message in a conversation."""

    conversation_id: uuid.UUID
    seq: int
    role: Literal["user", "assistant"]
    content: str
    is_partial: bool
    created_at: datetime


class ChatConversationSummary(IDSchema, TimestampSchema):
    """
    Listing payload.

    Deliberately excludes cv_text / job_description: both are multi-KB and
    would bloat every response.
    """

    title: str
    last_message_at: datetime
    message_count: int
    is_archived: bool
    analyse_id: uuid.UUID | None = None
    score_global: int | None = None
    ai_provider: str
    ai_model: str


class ChatConversationDetail(ChatConversationSummary):
    """Full conversation, including the context snapshot."""

    cv_text: str | None = None
    job_description: str | None = None
    recommandations: list[dict[str, Any]] = Field(default_factory=list)
    language: str
