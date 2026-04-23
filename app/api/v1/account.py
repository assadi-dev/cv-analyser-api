from app.core.exceptions import BadRequestError
from app.schemas.auth import RemoveUserRequest
from app.services.auth_service import AuthService


from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user_id
from app.core.logging import get_logger
from app.schemas.common import MessageResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/account", tags=["Account"])


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