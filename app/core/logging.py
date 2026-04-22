"""
Structured JSON logging module.

All errors and events are written to rotating JSON log files
so they can be queried and displayed in the frontend later.
"""

import json
import logging
import traceback
import uuid
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from app.core.config import settings


# ---------------------------------------------------------------------------
# JSON formatter
# ---------------------------------------------------------------------------

class JsonFormatter(logging.Formatter):
    """
    Formats log records as single-line JSON objects.

    Each log entry is a self-contained JSON document with:
    - timestamp (ISO 8601, UTC)
    - level
    - logger name
    - message
    - module / function / line
    - extra fields passed via logger.info("msg", extra={...})
    - exception details when present
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Attach extra fields (e.g. user_id, request_id, path)
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "levelname", "levelno",
                "pathname", "filename", "module", "funcName",
                "lineno", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process",
                "message", "exc_info", "exc_text", "stack_info",
            }:
                log_entry[key] = value

        # Exception details
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        return json.dumps(log_entry, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Logger factory
# ---------------------------------------------------------------------------

def _build_file_handler(filename: str, max_bytes: int = 10_485_760, backup_count: int = 5) -> RotatingFileHandler:
    """Creates a rotating JSON file handler."""
    log_path = Path(settings.log_dir) / filename
    log_path.parent.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,   # 10 MB per file
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(JsonFormatter())
    return handler


def get_logger(name: str) -> logging.Logger:
    """
    Returns a named logger that writes structured JSON to file and console.

    Usage:
        logger = get_logger(__name__)
        logger.info("User logged in", extra={"user_id": "123"})
        logger.error("DB error", exc_info=True, extra={"query": "SELECT ..."})
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # Already configured

    level = getattr(logging, settings.log_level, logging.INFO)
    logger.setLevel(level)

    # File handler — all logs
    logger.addHandler(_build_file_handler("app.json"))

    # Separate file for errors only (easier to query from frontend)
    error_handler = _build_file_handler("errors.json")
    error_handler.setLevel(logging.ERROR)
    logger.addHandler(error_handler)

    # Console handler (human-readable in development)
    if not settings.is_production:
        console = logging.StreamHandler()
        console.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        logger.addHandler(console)

    logger.propagate = False
    return logger


# ---------------------------------------------------------------------------
# Request context logging helper
# ---------------------------------------------------------------------------

def log_request_error(
    logger: logging.Logger,
    *,
    error: Exception,
    status_code: int,
    path: str,
    method: str,
    user_id: str | None = None,
    request_id: str | None = None,
) -> None:
    """
    Standardized HTTP error logging.
    Ensures every API error has the same structured fields.
    """
    logger.error(
        f"HTTP {status_code} on {method} {path}",
        exc_info=error,
        extra={
            "status_code": status_code,
            "path": path,
            "method": method,
            "user_id": user_id,
            "request_id": request_id or str(uuid.uuid4()),
        },
    )
