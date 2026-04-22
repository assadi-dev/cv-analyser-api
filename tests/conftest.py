"""
pytest configuration and shared fixtures.
"""

import os

import pytest

# Set test environment before any app imports
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/jobmatch_test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-minimum-32-characters-long-for-testing")
os.environ.setdefault("BETTER_AUTH_SECRET", "test-better-auth-secret-32-chars-ok")
os.environ.setdefault("BETTER_AUTH_URL", "http://localhost:3000")
os.environ.setdefault("ENVIRONMENT", "development")
