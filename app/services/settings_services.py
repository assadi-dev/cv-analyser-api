from fastapi.exceptions import HTTPException
from app.core.exceptions import BadRequestError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import get_logger
from app.repositories.settings_repo import SettingsRepository

logger = get_logger(__name__)

class SettingsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings_repo = SettingsRepository(db)

    def create_user_settings(self, user_id: str) -> None:
        """
        Create the settings for a user.
        """
        self.settings_repo.create_settings(user_id)

    def get_user_settings(self, user_id: str) -> None:
        """
        Get the settings for a user.
        """
        self.settings_repo.get_settings(user_id)

    def update_user_settings(self, user_id: str, settings: dict) -> None:
        """
        Update the settings for a user.
        """
        self.settings_repo.update_settings(user_id, settings)

    def clear_all_user_settings(self, user_id: str) -> None:
        """
        Clear all the settings for a user.
        """
        self.settings_repo.clear_all_user_settings(user_id)