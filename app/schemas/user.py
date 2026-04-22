"""User and settings Pydantic schemas."""

import uuid
from typing import Literal

from pydantic import Field, field_validator, model_validator

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
    professional_title: str | None
    avatar_url: str | None
    auth_provider: str
    ai_provider: str
    ai_model: str
    preferred_language: str
    ats_threshold: int
    recommendation_detail: str
    is_active: bool
