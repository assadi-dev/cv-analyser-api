from app.schemas.preference import ProviderPreferencesResponse
from app.factory.preference_factory import PreferenceFactory
from typing import Any
from app.factory.user_factory import UserFactory
from app.schemas.user import UserProfileUpdateResponse
from app.repositories.user_repo import UserRepository
from app.schemas.preference import PreferencesResponseByUser
import uuid
from fastapi.exceptions import HTTPException
from app.core.exceptions import BadRequestError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import get_logger
from app.repositories.preference_repo import PreferenceRepository


logger = get_logger(__name__)

class PreferenceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.preference_repo = PreferenceRepository(db)
        self.user_repo = UserRepository(db)

    def create_user_settings(self, user_id: str) -> None:
        """
        Create the settings for a user.
        """
        self.preference_repo.create_settings(user_id)

    async def get_user_preferences(self, user_id: str) -> PreferencesResponseByUser:
        """
        Get the settings for a user.
        """
        preferences = await self.preference_repo.get_by_user_id(uuid.UUID(user_id))
        return PreferencesResponseByUser.model_validate(preferences)

    async def update_analysis_preferences(self, user_id: str, inputs: Any) -> PreferencesResponseByUser:
        """
        Update the analysis preferences for a user.
        """
        update_data = inputs.model_dump(exclude_none=True) if hasattr(inputs, "model_dump") else inputs
        
        user = await self.user_repo.get_by_id_with_preferences(uuid.UUID(user_id))
        
        # Update preferences relationship
        for key, value in update_data.items():
            if hasattr(user.preferences, key):
                setattr(user.preferences, key, value)
        
        await self.db.commit()
        await self.db.refresh(user)
        return PreferencesResponseByUser.model_validate(user.preferences)

    async def update_user_profile(self, user_id: str, inputs: Any) -> UserProfileUpdateResponse:
        """
        Update the profile for a user.
        """
        # Convert Pydantic model to dict if needed
        update_data = inputs.model_dump(exclude_none=True) if hasattr(inputs, "model_dump") else inputs

        existing_user = await self.user_repo.get_by_id(uuid.UUID(user_id))
        if not existing_user:
            raise BadRequestError("User not found")

        # Update the model instance
        UserFactory.update_request_to_model(existing_user, update_data)
        
        # Save changes to DB
        updated_user = await self.user_repo.update_user(existing_user)
        
        return UserProfileUpdateResponse.model_validate(updated_user)

    def clear_all_user_settings(self, user_id: str) -> None:
        """
        Clear all the settings for a user.
        """
        self.preference_repo.clear_all_user_settings(user_id)


    async def update_ai_provider(self, user_id: str, inputs: Any) -> ProviderPreferencesResponse:
        """
        Update the AI provider for a user.

        This is a full replace (PUT semantics): ai_api_key/ai_base_url are
        written as-is, including None, so switching to a provider that
        doesn't need a key (e.g. Ollama) clears the stored one. Setting
        attributes directly bypasses BaseRepository.update(), which skips
        None values (that skip is correct for partial/PATCH updates
        elsewhere, but would silently keep the old key here).
        """
        user = await self.user_repo.get_by_id_with_preferences(uuid.UUID(user_id))

        user.preferences.ai_provider = inputs.ai_provider
        user.preferences.ai_model = inputs.ai_model
        user.preferences.ai_base_url = inputs.ai_base_url
        user.preferences.ai_api_key_encrypted = inputs.ai_api_key

        await self.db.commit()
        await self.db.refresh(user)
        return ProviderPreferencesResponse.model_validate(user.preferences)