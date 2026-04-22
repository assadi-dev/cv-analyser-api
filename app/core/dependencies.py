"""
FastAPI dependency injection helpers.

Reusable dependencies for authentication, pagination, and common patterns.
"""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import UnauthorizedError
from app.core.security import decode_api_token

# ---------------------------------------------------------------------------
# Auth scheme
# ---------------------------------------------------------------------------

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str:
    """
    FastAPI dependency — extracts and validates the API token from Authorization header.

    Returns the authenticated user's ID (UUID string).

    Raises:
        UnauthorizedError: No token provided or token is invalid.

    Usage:
        @router.get("/items")
        async def list_items(user_id: str = Depends(get_current_user_id)):
            ...
    """
    if credentials is None:
        raise UnauthorizedError(detail="Authorization header is missing")

    return decode_api_token(credentials.credentials)


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

class PaginationParams:
    """
    Standard pagination dependency.

    Usage:
        @router.get("/items")
        async def list_items(pagination: PaginationParams = Depends()):
            offset = pagination.offset
            limit  = pagination.limit
    """

    def __init__(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> None:
        self.page = max(1, page)
        self.page_size = min(max(1, page_size), 100)

    @property
    def offset(self) -> int:
        """SQL OFFSET value."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """SQL LIMIT value."""
        return self.page_size
