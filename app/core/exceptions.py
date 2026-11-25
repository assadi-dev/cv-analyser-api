"""
Custom exception hierarchy for the application.

Every HTTP error maps to a typed exception class.
Handlers in main.py convert these to standardized JSON responses.
"""

from typing import Any


# ---------------------------------------------------------------------------
# Base application exception
# ---------------------------------------------------------------------------

class AppError(Exception):
    """
    Base class for all application exceptions.

    Attributes:
        status_code: HTTP status code to return.
        error_code:  Machine-readable error identifier (e.g. "USER_NOT_FOUND").
        detail:      Human-readable error message.
        context:     Optional extra data attached to the error.
    """

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        detail: str = "An unexpected error occurred",
        context: dict[str, Any] | None = None,
    ) -> None:
        self.detail = detail
        self.context = context or {}
        super().__init__(detail)


# ---------------------------------------------------------------------------
# 400 — Bad Request
# ---------------------------------------------------------------------------

class BadRequestError(AppError):
    """Malformed request or invalid input data."""
    status_code = 400
    error_code = "BAD_REQUEST"


class ValidationError(AppError):
    """Request body failed schema validation."""
    status_code = 422
    error_code = "VALIDATION_ERROR"


class FileTooLargeError(AppError):
    """Uploaded file exceeds the maximum allowed size."""
    status_code = 413
    error_code = "FILE_TOO_LARGE"


class UnsupportedFileTypeError(AppError):
    """Uploaded file has an unsupported MIME type or extension."""
    status_code = 415
    error_code = "UNSUPPORTED_FILE_TYPE"


# ---------------------------------------------------------------------------
# 401 — Unauthorized
# ---------------------------------------------------------------------------

class UnauthorizedError(AppError):
    """Missing or invalid authentication credentials."""
    status_code = 401
    error_code = "UNAUTHORIZED"

    def __init__(self, detail: str = "Authentication required") -> None:
        super().__init__(detail=detail)


class InvalidTokenError(AppError):
    """JWT token is malformed, tampered, or has wrong type."""
    status_code = 401
    error_code = "INVALID_TOKEN"

    def __init__(self, detail: str = "Invalid token") -> None:
        super().__init__(detail=detail)


class ExpiredTokenError(AppError):
    """JWT token has passed its expiration date."""
    status_code = 401
    error_code = "TOKEN_EXPIRED"

    def __init__(self, detail: str = "Token has expired") -> None:
        super().__init__(detail=detail)


# ---------------------------------------------------------------------------
# 403 — Forbidden
# ---------------------------------------------------------------------------

class ForbiddenError(AppError):
    """Authenticated user does not have permission for this resource."""
    status_code = 403
    error_code = "FORBIDDEN"

    def __init__(self, detail: str = "You do not have permission to access this resource") -> None:
        super().__init__(detail=detail)


# ---------------------------------------------------------------------------
# 404 — Not Found
# ---------------------------------------------------------------------------

class NotFoundError(AppError):
    """Requested resource does not exist."""
    status_code = 404
    error_code = "NOT_FOUND"

    def __init__(self, resource: str = "Resource", resource_id: str | None = None) -> None:
        detail = f"{resource} not found"
        if resource_id:
            detail = f"{resource} '{resource_id}' not found"
        super().__init__(detail=detail, context={"resource": resource, "id": resource_id})


# ---------------------------------------------------------------------------
# 409 — Conflict
# ---------------------------------------------------------------------------

class ConflictError(AppError):
    """Resource already exists or state conflict."""
    status_code = 409
    error_code = "CONFLICT"


class DuplicateError(ConflictError):
    """Entity with the same unique key already exists."""
    error_code = "DUPLICATE_ENTITY"

    def __init__(self, resource: str = "Resource", field: str = "field") -> None:
        super().__init__(
            detail=f"{resource} with this {field} already exists",
            context={"resource": resource, "field": field},
        )


# ---------------------------------------------------------------------------
# 422 — Unprocessable Entity
# ---------------------------------------------------------------------------

class UnprocessableError(AppError):
    """Request is well-formed but semantically invalid."""
    status_code = 422
    error_code = "UNPROCESSABLE"


class CVTextUnreadableError(UnprocessableError):
    """
    A CV was given but no text can be read from it (scanned PDF, image-only,
    corrupted). A code of its own lets the client tell the user it is the CV at
    fault and what to do, instead of a generic "unprocessable".
    """
    error_code = "CV_TEXT_UNREADABLE"


# ---------------------------------------------------------------------------
# 429 — Too Many Requests
# ---------------------------------------------------------------------------

class RateLimitError(AppError):
    """Client has sent too many requests in a given time window."""
    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"

    def __init__(self, detail: str = "Too many requests. Please try again later.") -> None:
        super().__init__(detail=detail)


# ---------------------------------------------------------------------------
# 500 — Internal Server Error
# ---------------------------------------------------------------------------

class InternalError(AppError):
    """Unexpected server-side error."""
    status_code = 500
    error_code = "INTERNAL_ERROR"


class DatabaseError(InternalError):
    """Database operation failed."""
    error_code = "DATABASE_ERROR"

    def __init__(self, detail: str = "A database error occurred") -> None:
        super().__init__(detail=detail)


# ---------------------------------------------------------------------------
# 502 — Bad Gateway
# ---------------------------------------------------------------------------

class AIProviderError(AppError):
    """External AI provider returned an error or is unavailable."""
    status_code = 502
    error_code = "AI_PROVIDER_ERROR"

    def __init__(self, provider: str = "AI provider", detail: str | None = None) -> None:
        super().__init__(
            detail=detail or f"{provider} is unavailable or returned an error",
            context={"provider": provider},
        )


class AuthServiceError(AppError):
    """better-auth service is unavailable."""
    status_code = 502
    error_code = "AUTH_SERVICE_ERROR"

    def __init__(self, detail: str = "Authentication service unavailable") -> None:
        super().__init__(detail=detail)
