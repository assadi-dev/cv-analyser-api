"""Auth schemas — token exchange and session."""

from pydantic import Field

from app.schemas.common import AppBaseModel


class TokenExchangeRequest(AppBaseModel):
    """Request body for the token exchange endpoint."""

    session_token: str = Field(
        ...,
        min_length=10,
        description="better-auth session token obtained after login",
    )


class TokenResponse(AppBaseModel):
    """Response after a successful token exchange."""

    api_token: str = Field(description="FastAPI autonomous JWT token")
    token_type: str = Field(default="bearer")
    expires_in_days: int = Field(description="Token validity in days")


class UserSessionInfo(AppBaseModel):
    """Minimal user info returned alongside the token."""

    id: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    avatar_url: str | None = None
