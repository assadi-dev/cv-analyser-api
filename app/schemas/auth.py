"""Auth schemas — token exchange and session."""

from app.schemas.encryption import DecryptionPayload
from datetime import datetime
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
    avatar_url: str | None = Field(None, description="User avatar URL")
    preferred_language: str | None = Field("fr", description="User preferred language")
    


class LoginRequest(AppBaseModel):
    """Request body for the token exchange endpoint."""
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")
    auth_provider: str = Field(..., description="Authentication provider")
    auth_provider_id: str | None = Field(None, description="Authentication provider ID")


class LoginResponse(AppBaseModel):
    """Response after a successful token exchange."""
    token: str = Field(description="FastAPI autonomous JWT token")
    type: str = Field(default="bearer")
    expires_at: datetime = Field(description="Token validity in days")


class RemoveUserRequest(AppBaseModel):
    """Request body for removing a user."""

    confirm: bool = Field(False, description="Confirmation")  


class TokenExchangeRequest(DecryptionPayload):
    """Request body for the token exchange endpoint."""
    pass



class TokenResponse(AppBaseModel):
    """Response after a successful token exchange."""

    token: str = Field(description="FastAPI autonomous JWT token")
    type: str = Field(default="bearer")
    expires_at: datetime = Field(description="Token validity in days")
    expires_in_days: int = Field(description="Token validity in days")


class UserSessionInfo(AppBaseModel):
    """Minimal user info returned alongside the token."""

    id: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    avatar_url: str | None = None


class JWTPayload(AppBaseModel):
    sub: str = Field(description="User ID")
    iat: datetime = Field(description="Token issuance time")
    exp: datetime = Field(description="Token expiration time")
    type: str = Field(description="Token type")
    
    