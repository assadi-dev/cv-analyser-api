"""
Application configuration module.

Loads all settings from environment variables with strict typing and validation.
"""

from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings — loaded from .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------
    app_name: str = Field(default="Job Optimizer API", description="Application display name")
    app_version: str = Field(default="0.1.0", description="Semantic version")
    debug: bool = Field(default=False, description="Enable debug mode")
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Deployment environment",
    )

    # -------------------------------------------------------------------------
    # Server
    # -------------------------------------------------------------------------
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1, le=65535)

    # -------------------------------------------------------------------------
    # Database
    # -------------------------------------------------------------------------
    database_url: str = Field(
        ...,
        description="Async PostgreSQL connection string (asyncpg driver)",
    )
    database_pool_size: int = Field(default=10, ge=1, le=100)
    database_max_overflow: int = Field(default=20, ge=0, le=100)

    # -------------------------------------------------------------------------
    # Security — FastAPI autonomous JWT
    # -------------------------------------------------------------------------
    secret_key: str = Field(
        ...,
        min_length=32,
        description="HMAC secret key for signing API tokens",
    )
    algorithm: str = Field(default="HS256")
    api_token_expire_days: int = Field(default=30, ge=1, le=365)



    # -------------------------------------------------------------------------
    # CORS
    # -------------------------------------------------------------------------
    allowed_origins: list[str] = Field(
        default=["http://localhost:3000"],
        description="List of allowed CORS origins",
    )

    # -------------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------------
    log_dir: str = Field(default="logs", description="Directory for JSON log files")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO"
    )

    # -------------------------------------------------------------------------
    # AI Provider defaults (fallback)
    # -------------------------------------------------------------------------
    default_ai_provider: str = Field(default="ollama")
    default_ai_model: str = Field(default="gemma4:latest")
    openai_api_key: str = Field(default="")
    default_ai_base_url: str = Field(default="http://localhost:11434")
    llm_temperature: float = Field(default=0.3)

    # -------------------------------------------------------------------------
    # File storage
    # -------------------------------------------------------------------------
    upload_dir: str = Field(default="uploads")
    max_cv_size_mb: int = Field(default=10, ge=1, le=50)
    cv_dir: str = Field(default="cv")
    secrets_dir: str = Field(default="secrets")

    # -------------------------------------------------------------------------
    # Allowed CV extensions
    # -------------------------------------------------------------------------
    allowed_cv_extensions: list[str] = Field(default=[".pdf", ".docx", ".txt"])
    allowed_cv_mime_types: list[str] = Field(default=["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain"])

    # -------------------------------------------------------------------------
    # OCR
    # -------------------------------------------------------------------------
    ocr_dpi: int = Field(default=300)
    # Tesseract language codes joined with "+". French first, English kept for
    # the technical terms French CVs are full of. Each code needs its traineddata
    # installed (apt: tesseract-ocr-fra; brew: tesseract-lang).
    ocr_languages: str = Field(default="fra+eng")
    ocr_image_bytes_format: str = Field(default="png")

    # -------------------------------------------------------------------------
    # Computed properties
    # -------------------------------------------------------------------------
    @property
    def max_cv_size_bytes(self) -> int:
        """Maximum CV file size in bytes."""
        return self.max_cv_size_mb * 1024 * 1024

    @property
    def is_production(self) -> bool:
        """True when running in production environment."""
        return self.environment == "production"

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure async driver is used."""
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "DATABASE_URL must use asyncpg driver: "
                "postgresql+asyncpg://user:pass@host:port/db"
            )
        return v


# Singleton — import this everywhere
settings = Settings()  # type: ignore[call-arg]



