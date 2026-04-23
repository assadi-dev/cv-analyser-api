"""User and settings Pydantic schemas."""

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
    first_name: str | None
    last_name: str | None
    full_name: str | None
    professional_title: str | None
    avatar_url: str | None
    auth_provider: str
    ai_provider: AIProvider
    ai_model: str
    preferred_language: Language
    ats_threshold: int
    recommendation_detail: RecommendationDetail
    is_active: bool

    @model_validator(mode="after")
    def set_full_name(self) -> "UserResponse":
        if self.first_name and self.last_name:
            self.full_name = f"{self.first_name} {self.last_name}"
        return self

    @model_validator(mode="before")
    @classmethod
    def extract_settings_fields(cls, data: Any) -> dict[str, Any]:
        """Extract settings fields from the related Settings object."""

        if not isinstance(data, dict):
            # It's an ORM object with a settings relationship
            if hasattr(data, "settings") and data.settings:
                settings = data.settings
                data.ai_provider = settings.ai_provider
                data.ai_model = settings.ai_model
                data.preferred_language = settings.preferred_language
                data.ats_threshold = settings.ats_threshold
                data.recommendation_detail = settings.recommendation_detail
            return data

        # It's already a dict, copy settings fields if available
        if "settings" in data and data["settings"]:
            settings = data["settings"]
            if isinstance(settings, dict):
                data["ai_provider"] = settings.get("ai_provider")
                data["ai_model"] = settings.get("ai_model")
                data["preferred_language"] = settings.get("preferred_language")
                data["ats_threshold"] = settings.get("ats_threshold")
                data["recommendation_detail"] = settings.get("recommendation_detail")

        return data



