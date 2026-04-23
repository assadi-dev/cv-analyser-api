"""User repository."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Data access layer for User entities."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(User, db)

    async def get_by_id_with_settings(self, user_id: uuid.UUID) -> User:
        """Fetches a user by ID with settings eagerly loaded. Raises NotFoundError if not found."""
        result = await self.db.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.settings))
        )
        user = result.unique().scalar_one_or_none()
        if user is None:
            raise NotFoundError(resource="User", resource_id=str(user_id))
        return user

    async def get_by_email(self, email: str) -> User | None:
        """Fetches a user by their email address."""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()


    async def create_user(self, user: User) -> User:
        """Persists a new user entity."""
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user


    async def get_or_create_from_session(
        self,
        better_auth_id: str,
        email: str,
        first_name: str | None = None,
        last_name: str | None = None,
        avatar_url: str | None = None,
        auth_provider: str = "email",
    ) -> tuple[User, bool]:
        """
        Syncs a user from better-auth session.
        If user doesn't exist by email, creates it.
        """
        user = await self.get_by_email(email)
        if user:
            return user, False

        # Create new user
        new_user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            avatar_url=avatar_url,
            auth_provider=auth_provider,
        )
        
        self.db.add(new_user)
        await self.db.flush()
        await self.db.refresh(new_user)
        return new_user, True


    async def update_user(self, user: User) -> User:
        """Updates an existing user."""
        return await self.update(user)


    async def delete_user(self, user: User) -> None:
        """Deletes an existing user."""
        await self.delete(user)


    async def get_user_by_id(self, user_id: str) -> User | None:
        """Fetches a user by their ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

   