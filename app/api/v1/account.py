from app.repositories.user_repo import UserRepository
from app.core.exceptions import NotFoundError
from app.schemas.user import UserResponse
from app.core.exceptions import BadRequestError
from app.schemas.auth import RemoveUserRequest
from app.services.auth_service import AuthService

import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user_id
from app.core.logging import get_logger
from app.schemas.common import MessageResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/account", tags=["Account"])

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user's full profile",
)
async def get_me(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:

    if not user_id:
        raise NotFoundError("User")

    repo = UserRepository(db)
    user = await repo.get_user_with_preferences(uuid.UUID(user_id))

 
    user.id = str(user.id)
    user_response = UserResponse.model_validate(user)
    
    return UserResponse.model_validate({
        "id": str(user.id),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": f"{user.first_name} {user.last_name}",
        "avatar_url": user.avatar_url,
        "auth_provider": user.auth_provider,
        "professional_title": user.professional_title,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "ai_provider": "ollama",
        "ai_model": "llama3.2",
        "preferred_language": "fr",
        "ats_threshold": 80,
        "recommendation_detail": "detailed",
        })




@router.post("/remove", response_model=MessageResponse, summary="Remove user account")
async def remove_user(
    body: RemoveUserRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) :
    """
    Remove account.
    """
    if not body.confirm:
        raise BadRequestError(detail="Account removal must be confirmed")

    auth_service = AuthService(db)
    await auth_service.remove_user(user_id=user_id)
    return MessageResponse(message="User account removed successfully")