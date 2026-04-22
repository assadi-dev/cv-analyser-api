"""User repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Data access layer for User entities."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> User | None:
        """Fetches a user by their email address."""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_better_auth_id(self, better_auth_id: str) -> User | None:
        """Fetches a user by their better-auth session user ID."""
        result = await self.db.execute(
            select(User).where(User.better_auth_id == better_auth_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create_from_session(
        self,
        *,
        better_auth_id: str,
        email: str,
        first_name: str | None = None,
        last_name: str | None = None,
        avatar_url: str | None = None,
        auth_provider: str = "email",
    ) -> tuple[User, bool]:
        """
        Gets an existing user by better_auth_id, or creates one.

        Returns:
            Tuple of (user, created) where created=True if a new user was created.
        """
        user = await self.get_by_better_auth_id(better_auth_id)
        if user:
            return user, False

        user = await self.create(
            better_auth_id=better_auth_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            avatar_url=avatar_url,
            auth_provider=auth_provider,
        )
        return user, True
