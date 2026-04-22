"""Contact repository."""

import uuid

from sqlalchemy import and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact
from app.repositories.base import BaseRepository
from app.schemas.candidature import ContactCreate


class ContactRepository(BaseRepository[Contact]):
    """Data access layer for Contact entities."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Contact, db)

    async def create_many(
        self,
        candidature_id: uuid.UUID,
        contacts: list[ContactCreate],
    ) -> list[Contact]:
        """Creates multiple contacts for a candidature in one flush."""
        created = []
        for c in contacts:
            contact = Contact(
                candidature_id=candidature_id,
                name=c.name,
                contact_type=c.contact_type,
                value=c.value,
            )
            self.db.add(contact)
            created.append(contact)
        await self.db.flush()
        return created

    async def replace_all(
        self,
        candidature_id: uuid.UUID,
        contacts: list[ContactCreate],
    ) -> list[Contact]:
        """Deletes existing contacts for a candidature and inserts new ones."""
        await self.db.execute(
            delete(Contact).where(Contact.candidature_id == candidature_id)
        )
        return await self.create_many(candidature_id, contacts)
