""" Settings repository. """

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

class PreferenceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_id(self) -> str:
        """
        Get the user ID from the settings.
        """
        return await self.get_by_key("user_id")

    async def set_user_id(self, user_id: str) -> None:
        """
        Set the user ID in the settings.
        """
        await self.set_key("user_id", user_id)


    async def create_settings(self,user_id: str) -> None:
        """
        Initialize default preferences for a user.
        """
        preference = Preference(
            user_id=user_id,
        
     
        )

        print(preference.ats_threshold)

    """     self.db.add(preference)
        await self.db.commit()
        await self.db.refresh(preference)
        return preference """

    async def get_settings(self, user_id: str) -> dict:
        """
        Get the settings for a user.
        """
        # TODO: implement the retrieval of the settings
        pass

    async def update_settings(self, user_id: str, settings: dict) -> None:
        """
        Update the settings for a user.
        """
        # TODO: implement the update of the settings
        pass

    async def clear_all_user_settings(self, user_id: str) -> None:
        """
        Delete all the settings for a user.
        """
        # TODO: implement the deletion of the settings
        pass