"""
Job Optimizer API — FastAPI application entry point.

Configures the app, registers routers, exception handlers,
and lifecycle events (startup / shutdown).
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import settings
from app.core.database import connect_db, disconnect_db
from app.core.handlers import register_exception_handlers
from app.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handles application startup and shutdown events."""
    # Startup
    logger.info(
        "Starting Job Optimizer API",
        extra={"version": settings.app_version, "environment": settings.environment},
    )
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.log_dir).mkdir(parents=True, exist_ok=True)
    await connect_db()

    yield

    # Shutdown
    logger.info("Shutting down Job Optimizer API")
    await disconnect_db()


# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "AI-powered personal job application tracker. "
        "Analyses CV vs job offers, tracks candidatures, and provides recommendations."
    ),
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # allow_headers covers the request side only — without expose_headers a
    # browser cannot read X-Conversation-Id off the chat stream response.
    expose_headers=["X-Conversation-Id"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

register_exception_handlers(app)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

from app.api.v1.analyses import router as analyses_router
from app.api.v1.auth import router as auth_router
from app.api.v1.candidatures import router as candidatures_router
from app.api.v1.cvs import router as cvs_router
from app.api.v1.preferences import router as preferences_router
from app.api.v1.account import router as account_router
from app.api.v1.chat import router as chat_router
from app.api.v1.kanban import router as kanban_router

API_PREFIX = "/api/v1"

app.include_router(account_router, prefix=API_PREFIX)
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(candidatures_router, prefix=API_PREFIX)
app.include_router(cvs_router, prefix=API_PREFIX)
app.include_router(analyses_router, prefix=API_PREFIX)
app.include_router(preferences_router, prefix=API_PREFIX)
app.include_router(chat_router, prefix=API_PREFIX)
app.include_router(kanban_router, prefix=API_PREFIX)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["System"], summary="Health check")
async def health_check() -> dict[str, str]:
    """Returns application status. Used by load balancers and monitoring."""
    return {
        "status": "ok",
        "version": settings.app_version,
        "environment": settings.environment,
    }
