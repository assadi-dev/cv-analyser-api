"""
Auth router — token exchange endpoint.

This is the ONLY bridge between better-auth (Next.js) and FastAPI.
After the exchange, FastAPI operates fully autonomously with its own JWT.
"""

from app.repositories.preference_repo import PreferenceRepository
from app.factory.user_factory import UserFactory
from datetime import datetime
from app.services.encryption_serrvice import EncryptionService
from app.factory import user_factory
from app.factory.token_response_factory import TokenResponseFactory
from app.core.security import get_jwt_payload
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
from app.schemas.auth import RegisterRequest, TokenExchangeRequest, TokenResponse
from app.models.user import User

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register",response_model=TokenResponse,summary="Register a new user")
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    
) -> TokenResponse:
    """
    Register a new user.
    """
    auth_service = AuthService(db)
    user = await auth_service.register_user(body)
    response = TokenResponseFactory.build_token_response(str(user.id))
    logger.info("User registered successfully", extra={"user_id": str(user.id)})
    return response


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
    response = TokenResponseFactory.build_token_response(str(user.id))
    logger.info("User logged in successfully", extra={"user_id": str(user.id)})
    return response




@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Obtain a FastAPI API token",
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

    encryptionService = EncryptionService()
    decrypted_data = encryptionService.decrypt(body)
    user_factory = UserFactory.decrypt_request_to_user_model(decrypted_data)

    # Step 2 — Upsert user in FastAPI DB
    user_repo = UserRepository(db)
    user, created = await user_repo.get_or_create_from_session(
            email=user_factory.email,
            first_name=user_factory.first_name,
            last_name=user_factory.last_name,
            avatar_url=user_factory.avatar_url,
            professional_title=user_factory.professional_title,
            auth_provider=user_factory.auth_provider,
        ) 
    

    if created:
        preference_repo = PreferenceRepository(db)
        await preference_repo.create_settings(str(user.id))
        logger.info(f"User preferences created successfully")
        logger.info("New user created via token exchange", extra={"user_id": str(user.id)})


    # Step 3 — Generate FastAPI autonomous JWT
    response = TokenResponseFactory.build_token_response(str(user.id))

    logger.info(
        "API token issued",
        extra={"user_id": str(user.id), "new_user": created},
    )

    return response
