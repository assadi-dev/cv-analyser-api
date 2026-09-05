from app.schemas.user import AIProvider
from datetime import datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from app.schemas.common import AppBaseModel, IDSchema, TimestampSchema


class PreferenceCreate(AppBaseModel):
    """Create preference request."""
    user_id: str = Field(..., description="User ID")
    ai_provider: str = Field(..., description="AI provider")
    ai_model: str = Field(..., description="AI model")
    ai_api_key_encrypted: str | None = Field(None, description="AI API key encrypted")
    ai_base_url: str | None = Field(None, description="AI Provider base URL")
    preferred_language: str = Field(..., description="Preferred language")
    ats_threshold: int = Field(..., description="ATS threshold")
    recommendation_detail: str = Field(..., description="Recommendation detail")


class PreferenceResponse(AppBaseModel):
    """Preference response."""
    user_id: str = Field(..., description="User ID")
    ai_provider: str = Field(..., description="AI provider")
    ai_model: str = Field(..., description="AI model")
    ai_base_url: str | None = Field(None, description="AI Provider base URL")
    preferred_language: str = Field(..., description="Preferred language")
    ats_threshold: int = Field(..., description="ATS threshold")
    recommendation_detail: str = Field(..., description="Recommendation detail")


class PreferenceUpdateRequest(AppBaseModel):
    """Update preference request."""
    ai_provider: str | None = Field(None, description="AI provider")
    ai_model: str | None = Field(None, description="AI model")
    ai_api_key_encrypted: str | None = Field(None, description="AI API key encrypted")
    ai_base_url: str | None = Field(None, description="AI Provider base URL")
    preferred_language: str | None = Field(None, description="Preferred language")
    ats_threshold: int | None = Field(None, description="ATS threshold")
    recommendation_detail: str | None = Field(None, description="Recommendation detail")



class PreferencesResponseByUser(AppBaseModel):
    """User preferences response."""
    ai_provider: str = Field(..., description="AI provider")
    ai_model: str = Field(..., description="AI model")
    ai_base_url: str | None = Field(None, description="AI Provider base URL")
    preferred_language: str = Field(..., description="Preferred language")
    ats_threshold: int = Field(..., description="ATS threshold")
    recommendation_detail: str = Field(..., description="Recommendation detail")
    created_at: datetime = Field(..., description="Created at")
    updated_at: datetime = Field(..., description="Updated at")






class ProviderPreferencesResponse(AppBaseModel):
    """User preferences response."""
    ai_provider: str = Field(..., description="AI provider")
    ai_model: str = Field(..., description="AI model")
    ai_api_key: str | None = Field(
        default=None,
        description="Plain-text API key — stored encrypted at rest. "
                    "Omit for Ollama (no key required).",
    )
    ai_base_url: str | None = Field(
        default=None,
        description="Local Ollama server URL (e.g. http://localhost:11434)",
    )
    preferred_language: str = Field(..., description="Preferred language")

    @model_validator(mode="before")
    @classmethod
    def extract_provider_preferences(cls, data: Any) -> Any:
        """Extract provider preferences from the related preferences object."""

        if not isinstance(data, dict):
            # It's an ORM object with a preferences relationship
            preferences = getattr(data, "preferences", None)
            if preferences:
                # Create a dict with all required fields
                result = {
                    # Flattened preference fields
                    "id": str(preferences.id),
                    "ai_provider": preferences.ai_provider,
                    "ai_model": preferences.ai_model,
                    "ai_api_key": preferences.ai_api_key_encrypted,
                    "ai_base_url": preferences.ai_base_url,
                    "preferred_language": preferences.preferred_language,
                
                }
                return result
            return data

        # It's already a dict, copy preferences fields if available
        if "preferences" in data and data["preferences"]:
            preferences = data["preferences"]
            if isinstance(preferences, dict):
                data["ai_provider"] = preferences.get("ai_provider")
                data["ai_model"] = preferences.get("ai_model")
                data["ai_api_key"] = preferences.get("ai_api_key_encrypted")
                data["ai_base_url"] = preferences.get("ai_base_url")
                data["preferred_language"] = preferences.get("preferred_language")
            

        return data