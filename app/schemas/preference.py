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
