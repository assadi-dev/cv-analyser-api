"""
pytest configuration and shared fixtures.
"""

import os

import pytest

# Set test environment before any app imports.
#
# DATABASE_URL is forced, never defaulted: pydantic-settings gives the
# environment priority over .env, and this is the guard that keeps a test run
# from ever touching the development database. The URL is derived from .env so
# it works with the credentials already on this machine — same server, same
# role, a separate `<db>_test` database that tests may freely create and drop.
def _test_database_url() -> str:
    env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    dev_url = ""
    if os.path.exists(env_file):
        with open(env_file) as fh:
            for line in fh:
                line = line.strip()
                if line.startswith("DATABASE_URL="):
                    dev_url = line.split("=", 1)[1].strip().strip("\'\"")
                    break
    if not dev_url:
        return "postgresql+asyncpg://postgres:postgres@localhost:5432/cv_analyser_test"
    base, _, name = dev_url.rpartition("/")
    name = name.split("?")[0]
    return f"{base}/{name}_test"


TEST_DATABASE_URL = _test_database_url()
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("SECRET_KEY", "test-secret-key-minimum-32-characters-long-for-testing")
os.environ.setdefault("BETTER_AUTH_SECRET", "test-better-auth-secret-32-chars-ok")
os.environ.setdefault("BETTER_AUTH_URL", "http://localhost:3000")
os.environ.setdefault("ENVIRONMENT", "development")


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------
#
# There is no dedicated test database, so these run against the configured
# one — and must never leave anything behind. Every test gets a session bound
# to a connection whose outer transaction is always rolled back.
#
# `join_transaction_mode="create_savepoint"` is what makes that airtight: code
# under test that calls `session.commit()` (some repository methods still do)
# only releases a savepoint, so the outer transaction stays open and the
# rollback below still undoes everything.
#
# The engine is created per test rather than reusing `app.core.database.engine`:
# that one is module-level and would carry connections across event loops.

import uuid as _uuid
from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool


@pytest.fixture(scope="session", autouse=True)
def _prepare_test_database():
    """
    Creates the test database once per run and brings it to the current head.

    Alembic is used rather than `create_all` so the tests exercise the schema
    the application actually ships — constraints included. The Kanban tests in
    particular depend on the DEFERRABLE unique constraint, which only exists
    because a migration created it.
    """
    import asyncio

    import asyncpg
    from alembic import command
    from alembic.config import Config

    root = os.path.dirname(os.path.dirname(__file__))
    url = TEST_DATABASE_URL.replace("+asyncpg", "")
    admin_url, _, db_name = url.rpartition("/")

    async def ensure_database() -> None:
        conn = await asyncpg.connect(f"{admin_url}/postgres")
        try:
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", db_name
            )
            if not exists:
                await conn.execute(f'CREATE DATABASE "{db_name}"')
        finally:
            await conn.close()

    asyncio.run(ensure_database())

    cfg = Config(os.path.join(root, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(root, "migrations"))
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.upgrade(cfg, "head")
    yield


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """A session whose writes are always rolled back."""
    from app.core.config import settings

    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    conn = await engine.connect()
    trans = await conn.begin()
    session = AsyncSession(
        bind=conn,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        await session.close()
        await trans.rollback()
        await conn.close()
        await engine.dispose()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    """A throwaway user owning the fixtures below. Rolled back with the test."""
    from app.models.user import User

    user = User(
        email=f"kanban-test-{_uuid.uuid4()}@example.test",
        auth_provider="local",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def other_user(db_session: AsyncSession):
    """A second user, to prove board operations never cross ownership."""
    from app.models.user import User

    user = User(
        email=f"kanban-other-{_uuid.uuid4()}@example.test",
        auth_provider="local",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user
