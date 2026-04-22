"""
Auth router — token exchange endpoint.

This is the ONLY bridge between better-auth (Next.js) and FastAPI.
After the exchange, FastAPI operates fully autonomously with its own JWT.
"""

from app.schemas.auth import LoginRequest
from app.services.auth_service import AuthService
from fastapi.exceptions import HTTPException
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import create_api_token, verify_better_auth_session
from app.repositories.user_repo import UserRepository
from app.schemas.auth import RegisterRequest, RegisterResponse, TokenExchangeRequest, TokenResponse, UserSessionInfo
from app.models.user import User

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register",response_model=RegisterResponse,summary="Register a new user")
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    
) -> RegisterResponse:
    """
    Register a new user.
    """
    auth_service = AuthService(db)
    user = await auth_service.register_user(body)
    api_token = create_api_token(str(user.id))

    return RegisterResponse(
        api_token=api_token,
        token_type="bearer",
        expires_in_days=settings.api_token_expire_days,
    )


@router.post("/login",response_model=TokenResponse,summary="Login a user")
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
    
) -> TokenResponse:
    """
    Login a user.
    """
    auth_service = AuthService(db)
    user = await auth_service.login_user(body)
    api_token = create_api_token(str(user.id))

    return TokenResponse(
        api_token=api_token,
        token_type="bearer",
        expires_in_days=settings.api_token_expire_days,
    )


      


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Exchange better-auth session for a FastAPI API token",
    description=(
        "Called once after login on the Next.js frontend. "
        "Validates the better-auth session token, creates/syncs the user in the "
        "FastAPI database, and returns a long-lived autonomous JWT token. "
        "All subsequent API calls use this token — better-auth is never contacted again."
    ),
)
async def exchange_token(
    body: TokenExchangeRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Token exchange flow:
    1. Validate better-auth session token (single HTTP call to Next.js)
    2. Upsert user in FastAPI database
    3. Generate and return a FastAPI autonomous JWT
    """
    # Step 1 — Validate better-auth session
    session_user = await verify_better_auth_session(body.session_token)

    better_auth_id: str = session_user.get("id", "")
    email: str = session_user.get("email", "")

    logger.info(
        "Token exchange initiated",
        extra={"better_auth_id": better_auth_id, "email": email},
    )

    # Step 2 — Upsert user in FastAPI DB
    user_repo = UserRepository(db)
    user, created = await user_repo.get_or_create_from_session(
        better_auth_id=better_auth_id,
        email=email,
        first_name=session_user.get("name", "").split(" ")[0] if session_user.get("name") else None,
        last_name=" ".join(session_user.get("name", "").split(" ")[1:]) or None,
        avatar_url=session_user.get("image"),
        auth_provider=session_user.get("provider", "email"),
    )

    if created:
        logger.info("New user created via token exchange", extra={"user_id": str(user.id)})

    # Step 3 — Generate FastAPI autonomous JWT
    api_token = create_api_token(str(user.id))

    logger.info(
        "API token issued",
        extra={"user_id": str(user.id), "new_user": created},
    )

    return TokenResponse(
        api_token=api_token,
        token_type="bearer",
        expires_in_days=settings.api_token_expire_days,
    )
