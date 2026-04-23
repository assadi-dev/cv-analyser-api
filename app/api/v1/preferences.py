"""
Settings router — user profile, AI provider, and preferences.
"""

from app.schemas.user import UserProfileUpdateResponse
from app.services.preference_services import PreferenceService
from fastapi import APIRouter, Depends, HTTPException
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user_id
from app.core.logging import get_logger
from app.repositories.user_repo import UserRepository
from app.schemas.common import MessageResponse
from app.schemas.user import (
    AIProviderTestResponse,
    AIProviderUpdate,
    UserPreferencesUpdate,
    UserProfileUpdate,
    UserResponse,
)
from app.schemas.preference import PreferencesResponseByUser

logger = get_logger(__name__)
router = APIRouter(prefix="/preferences", tags=["Preferences"])

@router.get(
    "/profile",
    response_model=PreferencesResponseByUser,
    summary="Get user profile preferences",
)
async def get_preferences(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> PreferencesResponseByUser:
    service = PreferenceService(db)
    preferences = await service.get_user_preferences(user_id)
    return preferences

@router.patch(
    "/profile",
    response_model=UserProfileUpdateResponse,
    summary="Update user profile (name, title)",
)
async def update_profile(
    body: UserProfileUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> UserProfileUpdateResponse:
    preference_service = PreferenceService(db)
    result = await preference_service.update_user_profile(user_id, body)
    return result


@router.patch(
    "/analysis",
    response_model=UserResponse,
    summary="Update analysis preferences (language, ATS threshold, detail level)",
)
async def update_preferences(
    body: UserPreferencesUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    preference_service = PreferenceService(db)
    # We want a UserResponse, so we might need a method that returns the full user
    user = await preference_service.update_analysis_preferences(user_id, body)
    return UserResponse.model_validate(user)


@router.put(
    "/ai-provider",
    response_model=UserResponse,
    summary="Set active AI provider and API key",
)
async def update_ai_provider(
    body: AIProviderUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    from app.services.provider_service import ProviderService

    repo = UserRepository(db)
    user = await repo.get_by_id_with_preferences(uuid.UUID(user_id))

    # Encrypt API key before storing
    encrypted_key: str | None = None
    if body.ai_api_key:
        encrypted_key = ProviderService.encrypt_api_key(body.ai_api_key)

    await repo.update(
        user.preferences,
        ai_provider=body.ai_provider,
        ai_model=body.ai_model,
        ai_api_key_encrypted=encrypted_key,
    )
    await db.commit()

    logger.info(
        "AI provider updated",
        extra={"user_id": user_id, "provider": body.ai_provider, "model": body.ai_model},
    )
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.post(
    "/ai-provider/test",
    response_model=AIProviderTestResponse,
    summary="Test connection to the configured AI provider",
)
async def test_ai_provider(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> AIProviderTestResponse:
    from app.services.provider_service import ProviderService

    repo = UserRepository(db)
    user = await repo.get_by_id_with_preferences(uuid.UUID(user_id))

    return await ProviderService.test_provider(user)


