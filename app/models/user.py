"""
User ORM model.

Represents an authenticated user. The identity is managed by better-auth
on the Next.js side; FastAPI stores only the necessary profile data.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.candidature import Candidature
    from app.models.cv import CV


class User(BaseModel):
    """Application user profile."""

    __tablename__ = "users"

    # -------------------------------------------------------------------------
    # Identity (synced from better-auth at token exchange)
    # -------------------------------------------------------------------------
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    better_auth_id: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
        comment="User ID from better-auth session",
    )
    auth_provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="email",
        comment="Authentication provider: email | google | linkedin",
    )

    # -------------------------------------------------------------------------
    # Profile
    # -------------------------------------------------------------------------
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    professional_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # -------------------------------------------------------------------------
    # AI provider preferences (stored encrypted)
    # -------------------------------------------------------------------------
    ai_provider: Mapped[str] = mapped_column(
        String(50), nullable=False, default="openai"
    )
    ai_model: Mapped[str] = mapped_column(
        String(100), nullable=False, default="gpt-4o"
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
    cvs: Mapped[list["CV"]] = relationship(
        "CV", back_populates="user", cascade="all, delete-orphan"
    )
    candidatures: Mapped[list["Candidature"]] = relationship(
        "Candidature", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
