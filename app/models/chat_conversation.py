"""ChatConversation ORM model — a persistent chat thread with the AI assistant."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.chat_message import ChatMessage
    from app.models.user import User


class ChatConversation(BaseModel):
    """
    A chat thread between a user and the AI assistant.

    The analysis context (CV, job offer, score, recommendations) is stored as a
    snapshot on the conversation rather than read through a relationship. That
    is what makes a thread resumable even when no Analyse row exists — which is
    the case for the "anonymous" flow — and it keeps the thread reproducible if
    the underlying CV or analysis is later deleted.
    """

    __tablename__ = "chat_conversations"

    # -------------------------------------------------------------------------
    # Ownership — the single authorization anchor for the whole thread
    # -------------------------------------------------------------------------
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # -------------------------------------------------------------------------
    # Analysis context snapshot — taken at creation, never overwritten
    # -------------------------------------------------------------------------
    cv_text: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="CV text the assistant reasons on"
    )
    job_description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Job offer text the assistant reasons on"
    )
    score_global: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Match score (0-100) given to the model"
    )
    recommandations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="Snapshot of the analysis recommendations (same shape as analyses.recommandations)",
    )

    # -------------------------------------------------------------------------
    # Presentation
    # -------------------------------------------------------------------------
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Derived from the first question; user-editable",
    )
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Denormalised for cheap 'most recent first' ordering",
    )
    message_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    is_archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
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
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="fr")

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    # No link to Analyse here: the association is carried by
    # analyses.conversation_id, in that direction only.
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ChatMessage.seq",
    )

    __table_args__ = (
        # Covers WHERE user_id = ? ORDER BY last_message_at DESC
        Index("ix_chat_conversations_user_last_message", "user_id", "last_message_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<ChatConversation id={self.id} "
            f"user_id={self.user_id} "
            f"messages={self.message_count}>"
        )
