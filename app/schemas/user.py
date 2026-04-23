"""User and settings Pydantic schemas."""

from datetime import datetime
import uuid
from typing import Any, Literal

from pydantic import Field, model_validator

from app.schemas.common import AppBaseModel, IDSchema, TimestampSchema

AIProvider = Literal["openai", "anthropic", "groq", "mistral", "openrouter", "ollama"]
Language = Literal["fr", "en"]
RecommendationDetail = Literal["concise", "detailed"]


class UserProfileUpdate(AppBaseModel):
    """Schema for updating user profile info."""

    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    professional_title: str | None = Field(default=None, max_length=200)
    avatar_url: str | None = Field(default=None)
    email: str | None = Field(default=None)
    auth_provider: str | None = Field(default=None)
    email_verified: bool | None = Field(default=None)
    is_active: bool | None = Field(default=None)



class UserProfileUpdateResponse(AppBaseModel):
    """Schema for updating user profile info."""

    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    professional_title: str | None = Field(default=None, max_length=200)
    full_name: str | None = Field(default=None, max_length=200)
    avatar_url: str | None = Field(default=None)
    email: str | None = Field(default=None)
    auth_provider: str | None = Field(default=None)
    email_verified: bool | None = Field(default=None)
    is_active: bool | None = Field(default=None)
    created_at: datetime | None = Field(default=None)
    updated_at: datetime | None = Field(default=None)

    @model_validator(mode="after")
    @classmethod
    def set_full_name(cls, data: Any) -> Any:
        if data.first_name and data.last_name:
            data.full_name = f"{data.first_name} {data.last_name}"
        return data


class UserPreferencesUpdate(AppBaseModel):
    """Schema for updating analysis preferences."""

    preferred_language: Language | None = None
    ats_threshold: int | None = Field(default=None, ge=0, le=100)
    recommendation_detail: RecommendationDetail | None = None


class AIProviderUpdate(AppBaseModel):
    """Schema for updating the active AI provider and API key."""

    ai_provider: AIProvider
    ai_model: str = Field(..., min_length=1, max_length=100)
    ai_api_key: str | None = Field(
        default=None,
        description="Plain-text API key — stored encrypted at rest. "
                    "Omit for Ollama (no key required).",
    )
    ollama_base_url: str | None = Field(
        default=None,
        description="Local Ollama server URL (e.g. http://localhost:11434)",
    )

    @model_validator(mode="after")
    def validate_api_key(self) -> "AIProviderUpdate":
        if self.ai_provider != "ollama" and not self.ai_api_key:
            raise ValueError(f"ai_api_key is required for provider '{self.ai_provider}'")
        return self


class AIProviderTestResponse(AppBaseModel):
    """Response after testing an AI provider connection."""

    success: bool
    provider: str
    model: str
    message: str
    latency_ms: int | None = None


class UserResponse(IDSchema, TimestampSchema):
    """Full user profile response."""

    email: str
    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    professional_title: str | None = None
    avatar_url: str | None = None
    auth_provider: str
    ai_provider: AIProvider
    ai_model: str
    ai_api_key_encrypted: str | None = None
    ollama_base_url: str | None = None
    preferred_language: Language
    ats_threshold: int
    recommendation_detail: RecommendationDetail
    is_active: bool
    email_verified: bool
    created_at: datetime
    updated_at: datetime


    @model_validator(mode="before")
    @classmethod
    def extract_settings_fields(cls, data: Any) -> Any:
        """Extract settings fields from the related preferences object."""

        if not isinstance(data, dict):
            # It's an ORM object with a preferences relationship
            preferences = getattr(data, "preferences", None)
            if preferences:
                # Create a dict with all required fields
                result = {
                    "id": str(data.id),
                    "email": data.email,
                    "first_name": data.first_name,
                    "last_name": data.last_name,
                    "full_name": f"{data.first_name} {data.last_name}" if data.first_name and data.last_name else None,
                    "professional_title": data.professional_title,
                    "avatar_url": data.avatar_url,
                    "auth_provider": data.auth_provider,
                    "email_verified": data.email_verified,
                    "is_active": getattr(data, "is_active", True),
                    "created_at": getattr(data, "created_at", None),
                    "updated_at": getattr(data, "updated_at", None),
                    # Flattened preference fields
                    "ai_provider": preferences.ai_provider,
                    "ai_model": preferences.ai_model,
                    "ai_api_key_encrypted": preferences.ai_api_key_encrypted,
                    "ollama_base_url": preferences.ollama_base_url,
                    "preferred_language": preferences.preferred_language,
                    "ats_threshold": preferences.ats_threshold,
                    "recommendation_detail": preferences.recommendation_detail,
                 
                }
                return result
            return data

        # It's already a dict, copy preferences fields if available
        if "preferences" in data and data["preferences"]:
            preferences = data["preferences"]
            if isinstance(preferences, dict):
                data["ai_provider"] = preferences.get("ai_provider")
                data["ai_model"] = preferences.get("ai_model")
                data["ai_api_key_encrypted"] = preferences.get("ai_api_key_encrypted")
                data["ollama_base_url"] = preferences.get("ollama_base_url")
                data["preferred_language"] = preferences.get("preferred_language")
                data["ats_threshold"] = preferences.get("ats_threshold")
                data["recommendation_detail"] = preferences.get("recommendation_detail")
            


        return data




