"""
Settings router — user profile, AI provider, and preferences.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user_id
from app.core.exceptions import NotFoundError
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

logger = get_logger(__name__)
router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get(
    "/me",
    response_model=dict,
    summary="Get current user's full profile",
)
async def get_me(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    repo = UserRepository(db)
    user = await repo.get_by_id(uuid.UUID(user_id))
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "avatar_url": user.avatar_url,
        "auth_provider": user.auth_provider,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        }


@router.patch(
    "/profile",
    response_model=UserResponse,
    summary="Update user profile (name, title)",
)
async def update_profile(
    body: UserProfileUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    repo = UserRepository(db)
    user = await repo.get_by_id_with_settings(uuid.UUID(user_id))
    updated = await repo.update(user, **body.model_dump(exclude_none=True))
    return UserResponse.model_validate(updated)


@router.patch(
    "/preferences",
    response_model=UserResponse,
    summary="Update analysis preferences (language, ATS threshold, detail level)",
)
async def update_preferences(
    body: UserPreferencesUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    repo = UserRepository(db)
    user = await repo.get_by_id_with_settings(uuid.UUID(user_id))
    await repo.update(user.settings, **body.model_dump(exclude_none=True))
    await db.refresh(user)
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
    user = await repo.get_by_id_with_settings(uuid.UUID(user_id))

    # Encrypt API key before storing
    encrypted_key: str | None = None
    if body.ai_api_key:
        encrypted_key = ProviderService.encrypt_api_key(body.ai_api_key)

    await repo.update(
        user.settings,
        ai_provider=body.ai_provider,
        ai_model=body.ai_model,
        ai_api_key_encrypted=encrypted_key,
    )

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
    user = await repo.get_by_id_with_settings(uuid.UUID(user_id))

    return await ProviderService.test_provider(user)
