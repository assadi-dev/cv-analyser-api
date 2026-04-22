"""
Common Pydantic schemas shared across the application.

Defines reusable response wrappers, pagination, and base types.
"""

import uuid
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class AppBaseModel(BaseModel):
    """
    Base Pydantic model with shared configuration.
    All request/response schemas should inherit from this.
    """

    model_config = ConfigDict(
        from_attributes=True,       # Enable ORM mode (SQLAlchemy → Pydantic)
        populate_by_name=True,      # Allow both alias and field name
        str_strip_whitespace=True,  # Auto-strip whitespace from strings
        use_enum_values=True,
    )


class TimestampSchema(AppBaseModel):
    """Schema mixin for models with timestamps."""

    created_at: datetime
    updated_at: datetime


class IDSchema(AppBaseModel):
    """Schema mixin for models with a UUID primary key."""

    id: uuid.UUID


# ---------------------------------------------------------------------------
# Generic paginated response
# ---------------------------------------------------------------------------

class PaginatedResponse(AppBaseModel, Generic[T]):
    """
    Generic paginated list response.

    Example:
        PaginatedResponse[CandidatureResponse]
    """

    items: list[T]
    total: int = Field(description="Total number of items matching the query")
    page: int = Field(description="Current page number (1-indexed)")
    page_size: int = Field(description="Number of items per page")
    pages: int = Field(description="Total number of pages")

    @classmethod
    def build(
        cls,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse[T]":
        """Factory method to build a paginated response."""
        pages = max(1, -(-total // page_size))  # Ceiling division
        return cls(items=items, total=total, page=page, page_size=page_size, pages=pages)


# ---------------------------------------------------------------------------
# Standard message response
# ---------------------------------------------------------------------------

class MessageResponse(AppBaseModel):
    """Simple success message response."""

    message: str


class DeleteResponse(AppBaseModel):
    """Response after a successful deletion."""

    message: str = "Resource deleted successfully"
    id: uuid.UUID
