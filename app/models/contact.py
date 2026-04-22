"""Contact ORM model — linked to a Candidature."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.candidature import Candidature


class Contact(BaseModel):
    """
    A contact person associated with a job application.

    A candidature can have multiple contacts (recruiter, HR manager, etc.).
    """

    __tablename__ = "contacts"

    # -------------------------------------------------------------------------
    # Foreign key
    # -------------------------------------------------------------------------
    candidature_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidatures.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # -------------------------------------------------------------------------
    # Contact details
    # -------------------------------------------------------------------------
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="email",
        comment="Contact method type: email | phone"
    )
    value: Mapped[str] = mapped_column(
        String(255), nullable=False,
        comment="Email address or phone number"
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    candidature: Mapped["Candidature"] = relationship(
        "Candidature", back_populates="contacts"
    )

    def __repr__(self) -> str:
        return f"<Contact id={self.id} name={self.name} type={self.contact_type}>"
