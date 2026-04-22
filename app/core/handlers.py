"""
Global exception handlers for FastAPI.

Converts all application exceptions and unexpected errors
into standardized JSON responses with consistent shape.

Response format:
{
    "error": {
        "code":    "NOT_FOUND",
        "message": "User 'abc' not found",
        "context": { "resource": "User", "id": "abc" }
    },
    "request_id": "uuid"
}
"""

import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import AppError
from app.core.logging import get_logger, log_request_error

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Standard error response builder
# ---------------------------------------------------------------------------

def _error_response(
    *,
    status_code: int,
    error_code: str,
    message: str,
    context: dict[str, Any] | None = None,
    request_id: str,
) -> JSONResponse:
    """Builds a standardized JSON error response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": error_code,
                "message": message,
                "context": context or {},
            },
            "request_id": request_id,
        },
    )


# ---------------------------------------------------------------------------
# Handler registration
# ---------------------------------------------------------------------------

def register_exception_handlers(app: FastAPI) -> None:
    """
    Registers all exception handlers on the FastAPI app.
    Call this once during application startup.
    """

    # ------------------------------------------------------------------
    # Application custom exceptions
    # ------------------------------------------------------------------
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        request_id = str(uuid.uuid4())

        log_request_error(
            logger,
            error=exc,
            status_code=exc.status_code,
            path=str(request.url.path),
            method=request.method,
            request_id=request_id,
        )

        return _error_response(
            status_code=exc.status_code,
            error_code=exc.error_code,
            message=exc.detail,
            context=exc.context,
            request_id=request_id,
        )

    # ------------------------------------------------------------------
    # FastAPI / Pydantic validation errors (422)
    # ------------------------------------------------------------------
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        request_id = str(uuid.uuid4())

        # Format field errors into a clean list
        field_errors = [
            {
                "field": " → ".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
            for error in exc.errors()
        ]

        logger.warning(
            "Request validation failed",
            extra={
                "path": str(request.url.path),
                "method": request.method,
                "field_errors": field_errors,
                "request_id": request_id,
            },
        )

        return _error_response(
            status_code=422,
            error_code="VALIDATION_ERROR",
            message="Request validation failed",
            context={"field_errors": field_errors},
            request_id=request_id,
        )

    # ------------------------------------------------------------------
    # Pydantic v2 validation errors (from schema parsing)
    # ------------------------------------------------------------------
    @app.exception_handler(PydanticValidationError)
    async def pydantic_error_handler(
        request: Request, exc: PydanticValidationError
    ) -> JSONResponse:
        request_id = str(uuid.uuid4())

        logger.warning(
            "Pydantic schema validation error",
            extra={
                "path": str(request.url.path),
                "errors": exc.errors(),
                "request_id": request_id,
            },
        )

        return _error_response(
            status_code=422,
            error_code="SCHEMA_VALIDATION_ERROR",
            message="Data schema validation failed",
            context={"errors": exc.errors()},
            request_id=request_id,
        )

    # ------------------------------------------------------------------
    # Catch-all: unhandled exceptions (500)
    # ------------------------------------------------------------------
    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = str(uuid.uuid4())

        log_request_error(
            logger,
            error=exc,
            status_code=500,
            path=str(request.url.path),
            method=request.method,
            request_id=request_id,
        )

        # Never expose internal details in production
        from app.core.config import settings
        message = str(exc) if settings.debug else "An internal server error occurred"

        return _error_response(
            status_code=500,
            error_code="INTERNAL_ERROR",
            message=message,
            request_id=request_id,
        )
