from typing import Any, Literal

from pydantic import Field, model_validator

from app.schemas.common import AppBaseModel, IDSchema, TimestampSchema


class PreferenceCreate(AppBaseModel):
    """Create preference request."""
    user_id: str = Field(..., description="User ID")
    ai_provider: str = Field(..., description="AI provider")
    ai_model: str = Field(..., description="AI model")
    ai_api_key_encrypted: str | None = Field(None, description="AI API key encrypted")
    ollama_base_url: str | None = Field(None, description="Ollama base URL")
    preferred_language: str = Field(..., description="Preferred language")
    ats_threshold: int = Field(..., description="ATS threshold")
    recommendation_detail: str = Field(..., description="Recommendation detail")


class PreferenceResponse(AppBaseModel):
    """Preference response."""
    user_id: str = Field(..., description="User ID")
    ai_provider: str = Field(..., description="AI provider")
    ai_model: str = Field(..., description="AI model")
    preferred_language: str = Field(..., description="Preferred language")
    ats_threshold: int = Field(..., description="ATS threshold")
    recommendation_detail: str = Field(..., description="Recommendation detail")