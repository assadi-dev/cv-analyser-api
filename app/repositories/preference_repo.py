""" Settings repository. """

from app.schemas.preference import PreferencesResponseByUser
from app.factory.preference_factory import PreferenceFactory
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models.user import User
from app.models.preference import Preference
from app.repositories.base import BaseRepository
from app.core.logging import get_logger

logger = get_logger(__name__)

class PreferenceRepository(BaseRepository[Preference]):
    def __init__(self, db: AsyncSession):
        super().__init__(Preference, db)

    async def get_by_user_id(self, user_id: uuid.UUID) -> Preference:
        """
        Get the preferences for a user.
        """
        stmt = select(Preference).where(Preference.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_settings(self, user_id: str) -> Preference:
        """
        Initialize default preferences for a user.
        """
        preferences = PreferenceFactory.generate_model(user_id)
        self.db.add(preferences)
        await self.db.commit()
        await self.db.refresh(preferences)
        return preferences 

    async def update_preferences(self, user_id: uuid.UUID, inputs: dict) -> Preference:
        """
        Update the preferences for a user.
        """
        preferences = await self.get_by_user_id(user_id)
        if not preferences:
            raise NotFoundError("Preferences not found")
        
        updated = await self.update(preferences, **inputs)
        await self.db.commit()
        await self.db.refresh(updated)
        return updated

    async def clear_all_user_settings(self, user_id: uuid.UUID) -> None:
        """
        Delete all the preferences for a user.
        """
        from sqlalchemy import delete
        stmt = delete(Preference).where(Preference.user_id == user_id)
        await self.db.execute(stmt)
        await self.db.commit()