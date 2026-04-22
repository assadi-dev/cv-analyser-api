"""Analyse ORM model — stores AI analysis results."""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.candidature import Candidature
    from app.models.cv import CV


class Analyse(BaseModel):
    """
    Result of an AI analysis session.

    One candidature can have multiple analyses over time
    (e.g. after updating the CV).
    """

    __tablename__ = "analyses"

    # -------------------------------------------------------------------------
    # Foreign keys
    # -------------------------------------------------------------------------
    candidature_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidatures.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
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
    chat_history: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list,
        comment="Conversation history with the AI assistant"
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
    candidature: Mapped["Candidature"] = relationship(
        "Candidature", back_populates="analyses"
    )
    cv: Mapped["CV | None"] = relationship("CV", back_populates="analyses")

    def __repr__(self) -> str:
        return (
            f"<Analyse id={self.id} "
            f"score={self.score_global} "
            f"ats={self.score_ats}>"
        )
