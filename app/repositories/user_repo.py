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


    async def create_user(self, user: User) -> User:
        """Creates a new user."""
        return await self.create(user)


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

   