"""CV ORM model."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.analyse import Analyse
    from app.models.candidature import Candidature
    from app.models.user import User


class CV(BaseModel):
    """A resume file uploaded by a user."""

    __tablename__ = "cvs"

    # -------------------------------------------------------------------------
    # Foreign key
    # -------------------------------------------------------------------------
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # -------------------------------------------------------------------------
    # File metadata
    # -------------------------------------------------------------------------
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Display name of the CV file"
    )
    file_path: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Relative path to the stored file"
    )
    file_size_kb: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    extension: Mapped[str] = mapped_column(
        String(10), nullable=False, default=".pdf"
    )
    key: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Key to access the file"
    )
    mime_type: Mapped[str] = mapped_column(
        String(100), nullable=False, default="application/pdf"
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="Whether this CV is pre-selected for new analyses"
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    user: Mapped["User"] = relationship("User", back_populates="cvs")
    candidatures: Mapped[list["Candidature"]] = relationship(
        "Candidature", back_populates="cv"
    )
    analyses: Mapped[list["Analyse"]] = relationship(
        "Analyse", back_populates="cv"
    )

    def __repr__(self) -> str:
        return f"<CV id={self.id} name={self.name}>"
