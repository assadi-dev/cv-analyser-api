"""
User ORM model.

Represents an authenticated user. The identity is managed by better-auth
on the Next.js side; FastAPI stores only the necessary profile data.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.candidature import Candidature
    from app.models.cv import CV
    from app.models.settings import Settings


class User(BaseModel):
    """Application user profile."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
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
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

   
    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------

    settings: Mapped["Settings"] = relationship(
        "Settings", back_populates="user", cascade="all, delete-orphan"
    )
    cvs: Mapped[list["CV"]] = relationship(
        "CV", back_populates="user", cascade="all, delete-orphan"
    )
    candidatures: Mapped[list["Candidature"]] = relationship(
        "Candidature", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
