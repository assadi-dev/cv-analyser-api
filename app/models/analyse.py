"""Analyse ORM model — stores AI analysis results."""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.chat_conversation import ChatConversation
    from app.models.cv import CV
    from app.models.user import User


class Analyse(BaseModel):
    """
    Result of an AI analysis session.

    An analysis stands on its own: ownership lives on user_id, and the link to
    a candidature — when there is one — is carried by candidatures.analyse_id,
    in that direction only.
    """

    __tablename__ = "analyses"

    # -------------------------------------------------------------------------
    # Foreign keys
    # -------------------------------------------------------------------------
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Owner of the analysis — set even when there is no candidature",
    )
    cv_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cvs.id", ondelete="SET NULL"),
        nullable=True,
    )

    # -------------------------------------------------------------------------
    # Input (stored for audit / re-analysis)
    # -------------------------------------------------------------------------
    job_description: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Raw job offer text used for this analysis"
    )
    cv_text: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Extracted CV text used for this analysis"
    )

    # -------------------------------------------------------------------------
    # Scores (0-100)
    # -------------------------------------------------------------------------
    score_global: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Overall matching score (weighted average)"
    )
    score_ats: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="ATS compatibility score"
    )
    score_competences: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Technical skills matching score"
    )
    score_experience: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Experience relevance score"
    )

    # -------------------------------------------------------------------------
    # Keywords
    # -------------------------------------------------------------------------
    keywords_found: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list,
        comment="Job offer keywords found in the CV"
    )
    keywords_missing: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list,
        comment="Job offer keywords missing from the CV"
    )

    # -------------------------------------------------------------------------
    # AI output
    # -------------------------------------------------------------------------
    recommandations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list,
        comment="List of AI-generated recommendations"
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "chat_conversations.id",
            ondelete="SET NULL",
            name="fk_analyses_conversation_id",
        ),
        nullable=True,
        # unique: makes the 1:1 a guarantee rather than a convention, which is
        # what lets the chat service resolve its analysis with a reverse query.
        # Postgres allows any number of NULLs under a unique index, so
        # analyses without a conversation are unaffected.
        unique=True,
        comment="Chat conversation attached to this analysis, if any"
    )

    # -------------------------------------------------------------------------
    # Provider metadata
    # -------------------------------------------------------------------------
    ai_provider: Mapped[str] = mapped_column(
        String(50), nullable=False, default="openai"
    )
    ai_model: Mapped[str] = mapped_column(
        String(100), nullable=False, default="gpt-4o"
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    user: Mapped["User"] = relationship("User", back_populates="analyses")
    cv: Mapped["CV | None"] = relationship("CV", back_populates="analyses")
    conversation: Mapped["ChatConversation | None"] = relationship("ChatConversation")

    def __repr__(self) -> str:
        return (
            f"<Analyse id={self.id} "
            f"score={self.score_global} "
            f"ats={self.score_ats}>"
        )
