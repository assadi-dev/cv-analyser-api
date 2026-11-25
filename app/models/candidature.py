"""Candidature ORM model."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.analyse import Analyse
    from app.models.contact import Contact
    from app.models.cv import CV
    from app.models.kanban import Kanban
    from app.models.user import User


class Candidature(BaseModel):
    """
    A job application entry tracked by the user.

    Represents one job offer the user has analysed and/or applied to.
    """

    __tablename__ = "candidatures"

    # -------------------------------------------------------------------------
    # Foreign keys
    # -------------------------------------------------------------------------
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cv_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cvs.id", ondelete="SET NULL"),
        nullable=True,
        comment="CV used for this application",
    )
    analyse_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="AI analysis attached to this application, if any",
    )

    # -------------------------------------------------------------------------
    # Company & position
    # -------------------------------------------------------------------------
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    company_region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    company_country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    contract_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="CDI",
        comment="CDI | CDD | Freelance | Stage | Alternance"
    )
    work_mode: Mapped[str] = mapped_column(
        String(50), nullable=False, default="hybrid",
        comment="remote | hybrid | on-site"
    )

    # -------------------------------------------------------------------------
    # Source
    # -------------------------------------------------------------------------
    source_platform: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="e.g. LinkedIn, Indeed, WTTJ"
    )
    source_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
        comment="Job offer display name on the platform"
    )
    source_url: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Direct URL to the job offer"
    )

    # -------------------------------------------------------------------------
    # Job offer
    # -------------------------------------------------------------------------
    job_description: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Job offer text, kept with the application and used to pre-fill analyses"
    )

    # -------------------------------------------------------------------------
    # Status
    # -------------------------------------------------------------------------
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="to_send",
        comment="to_send | sent | interview | rejected | accepted",
        index=True,
    )

    # -------------------------------------------------------------------------
    # Notes
    # -------------------------------------------------------------------------
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    user: Mapped["User"] = relationship("User", back_populates="candidatures")
    cv: Mapped["CV | None"] = relationship("CV", back_populates="candidatures")
    contacts: Mapped[list["Contact"]] = relationship(
        "Contact", back_populates="candidature", cascade="all, delete-orphan"
    )
    # Single analysis, not a collection: the link is now carried here, so a
    # candidature points at one analysis rather than owning a history of them.
    # No cascade — the analysis belongs to the user and outlives the
    # candidature (the FK is ON DELETE SET NULL).
    analyse: Mapped["Analyse | None"] = relationship("Analyse")
    # Board placement. One row per candidature, created alongside it and
    # removed by CASCADE. See app/models/kanban.py for why `status` is
    # duplicated between the two tables.
    kanban: Mapped["Kanban | None"] = relationship(
        "Kanban", back_populates="candidature", cascade="all, delete-orphan",
        uselist=False,
    )

    def __repr__(self) -> str:
        return f"<Candidature id={self.id} company={self.company_name} job={self.job_title}>"
