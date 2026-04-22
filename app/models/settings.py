"""Settings ORM model."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User


class Settings(BaseModel):
    """User settings."""

    __tablename__ = "settings"
 
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    # -------------------------------------------------------------------------
    # AI provider preferences (stored encrypted)
    # -------------------------------------------------------------------------
    ai_provider: Mapped[str] = mapped_column(
        String(50), nullable=False, default="ollama"
    )
    ai_model: Mapped[str] = mapped_column(
        String(100), nullable=False, default="llama3.2"
    )
    ai_api_key_encrypted: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="User's AI provider API key — AES-256 encrypted at rest",
    )

    # -------------------------------------------------------------------------
    # Analysis preferences
    # -------------------------------------------------------------------------
    preferred_language: Mapped[str] = mapped_column(
        String(10), nullable=False, default="fr"
    )
    ats_threshold: Mapped[int] = mapped_column(
        Integer, nullable=False, default=70,
        comment="Minimum ATS score the user considers acceptable (0-100)"
    )
    recommendation_detail: Mapped[str] = mapped_column(
        String(20), nullable=False, default="detailed",
        comment="Level of detail for AI recommendations: concise | detailed"
    )


    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    user: Mapped["User"] = relationship("User", back_populates="settings")

    def __repr__(self) -> str:
        return f"<Settings id={self.id} user_id={self.user_id}>"