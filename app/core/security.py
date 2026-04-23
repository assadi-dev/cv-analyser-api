"""
Security module — FastAPI autonomous JWT system.

FastAPI generates and verifies its own tokens independently of better-auth.
The only bridge with better-auth is the token exchange endpoint (/auth/token).
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import bcrypt
from jose import JWTError, jwt

from app.core.config import settings
from app.core.exceptions import (
    ExpiredTokenError,
    InvalidTokenError,
    UnauthorizedError,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Password hashing (using bcrypt directly to avoid passlib bugs)
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Hashes a plain-text password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain-text password against a bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


# ---------------------------------------------------------------------------
# FastAPI API Token (autonomous JWT)
# ---------------------------------------------------------------------------

def create_api_token(user_id: str) -> str:
    """
    Generates a long-lived API token for FastAPI.

    This token is fully autonomous — FastAPI never calls better-auth
    to validate it after the initial token exchange.

    Args:
        user_id: The authenticated user's UUID string.

    Returns:
        Signed JWT string.
    """
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(days=settings.api_token_expire_days),
        "type": "api_token",
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    logger.info("API token created", extra={"user_id": user_id})
    return token


def decode_api_token(token: str) -> str:
    """
    Decodes and validates a FastAPI API token.

    Args:
        token: JWT string from Authorization header.

    Returns:
        user_id (str) extracted from the token subject claim.

    Raises:
        ExpiredTokenError: Token has passed its expiration date.
        InvalidTokenError: Token is malformed, tampered, or wrong type.
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
    except JWTError as exc:
        if "expired" in str(exc).lower():
            raise ExpiredTokenError() from exc
        raise InvalidTokenError() from exc

    user_id: str | None = payload.get("sub") 
    token_type: str | None = payload.get("type")

    if not user_id:
        raise InvalidTokenError(detail="Token missing subject claim")

    if token_type != "api_token":
        raise InvalidTokenError(detail="Invalid token type")

    if user_id == "None":
        return None

    return user_id


# ---------------------------------------------------------------------------
# Better Auth token exchange — called ONCE during login
# ---------------------------------------------------------------------------

async def verify_better_auth_session(session_token: str) -> dict[str, Any]:
    """
    Validates a better-auth session token by calling the Next.js auth endpoint.

    This is called ONLY during the token exchange (/api/v1/auth/token).
    After the exchange, FastAPI uses its own JWT — no further calls needed.

    Args:
        session_token: The session token issued by better-auth.

    Returns:
        User data dict from better-auth.

    Raises:
        UnauthorizedError: If the session is invalid or expired.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.better_auth_url}/api/auth/get-session",
                headers={"Authorization": f"Bearer {session_token}"},
            )

        if response.status_code != 200:
            logger.warning(
                "better-auth session validation failed",
                extra={
                    "status_code": response.status_code,
                    "better_auth_url": settings.better_auth_url,
                    "response_text": response.text[:500] if response.text else None,
                },
            )
            raise UnauthorizedError(detail="Invalid or expired session")

        try:
            data: dict[str, Any] = response.json()
        except Exception as exc:
            logger.error(
                "Failed to parse better-auth response as JSON",
                exc_info=exc,
                extra={"response_text": response.text[:500]},
            )
            raise UnauthorizedError(detail="Invalid session response format") from exc

        if not data or not isinstance(data, dict):
            logger.warning(
                "better-auth response is empty or not a dict",
                extra={"response": str(data)[:100]},
            )
            raise UnauthorizedError(detail="Invalid session response format")

        user = data.get("user")

        if not user:
            raise UnauthorizedError(detail="No user in session response")

        return user

    except httpx.RequestError as exc:
        logger.error(
            "Failed to reach better-auth server",
            exc_info=exc,
            extra={"better_auth_url": settings.better_auth_url},
        )
        raise UnauthorizedError(detail="Authentication service unavailable") from exc
