"""
Preference ORM model.

This model stores user preferences for the AI provider and analysis.
"""

from app.core.preferences import PreferencesDefaultConfigs
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User


class Preference(BaseModel):
    """User preferences."""

    __tablename__ = "preferences"
    
 
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    # -------------------------------------------------------------------------
    # AI provider preferences (stored encrypted)
    # -------------------------------------------------------------------------
    ai_provider: Mapped[str] = mapped_column(
        String(50), nullable=False, default=PreferencesDefaultConfigs.ai_provider
    )
    ai_model: Mapped[str] = mapped_column(
        String(100), nullable=False, default=PreferencesDefaultConfigs.ai_model
    )
    ai_api_key_encrypted: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="User's AI provider API key — AES-256 encrypted at rest",
    )
    ai_base_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="User's AI provider base URL",
    )
    # -------------------------------------------------------------------------
    # Analysis preferences
    # -------------------------------------------------------------------------
    preferred_language: Mapped[str] = mapped_column(
        String(10), nullable=False, default=PreferencesDefaultConfigs.preferred_language
    )
    ats_threshold: Mapped[int] = mapped_column(
        Integer, nullable=False, default=PreferencesDefaultConfigs.ats_threshold,
        comment="Minimum ATS score the user considers acceptable (0-100)"
    )
    recommendation_detail: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PreferencesDefaultConfigs.recommendation_detail,
        comment="Level of detail for AI recommendations: concise | detailed"
    )


    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    user: Mapped["User"] = relationship("User", back_populates="preferences")

    def __repr__(self) -> str:
        return f"<Preference id={self.id} user_id={self.user_id}>"