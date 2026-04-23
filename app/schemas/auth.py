"""Auth schemas — token exchange and session."""

from pydantic import Field

from app.schemas.common import AppBaseModel


class RegisterRequest(AppBaseModel):
    """Request body for the token exchange endpoint."""
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")
    first_name: str | None = Field(None, description="User first name")
    last_name: str | None = Field(None, description="User last name")
    auth_provider: str = Field(..., description="Authentication provider")
    auth_provider_id: str | None = Field(None, description="Authentication provider ID")
    professional_title: str | None = Field(None, description="User professional title")
    email_verified: bool = Field(False, description="Email verification status")
    preferred_language: str | None = Field("fr", description="User preferred language")
    


class RegisterResponse(AppBaseModel):
    """Response after a successful token exchange."""
    api_token: str = Field(description="FastAPI autonomous JWT token")
    token_type: str = Field(default="bearer")
    expires_in_days: int = Field(description="Token validity in days")


class LoginRequest(AppBaseModel):
    """Request body for the token exchange endpoint."""
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")
    auth_provider: str = Field(..., description="Authentication provider")
    auth_provider_id: str | None = Field(None, description="Authentication provider ID")


class LoginResponse(AppBaseModel):
    """Response after a successful token exchange."""
    api_token: str = Field(description="FastAPI autonomous JWT token")
    token_type: str = Field(default="bearer")
    expires_in_days: int = Field(description="Token validity in days")


class RemoveUserRequest(AppBaseModel):
    """Request body for removing a user."""

    confirm: bool = Field(False, description="Confirmation")  


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
