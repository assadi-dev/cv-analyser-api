"""CV repository."""

from app.core.exceptions import NotFoundError
import uuid

from sqlalchemy import and_, select, update,delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cv import CV
from app.repositories.base import BaseRepository


class CVRepository(BaseRepository[CV]):
    """Data access layer for CV entities."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(CV, db)

    async def create_cv(self, model: CV) -> CV:
        self.db.add(model)
        await self.db.commit()
        await self.db.refresh(model)
        return model
        

    async def update_cv(self,id:uuid.UUID, inputs: dict) -> CV:

        cv = await self.get_by_id(id)
        if not cv:
            raise NotFoundError(resource="CV", resource_id=id)

        updated = await self.update(cv, **inputs)
        await self.db.commit()
        await self.db.refresh(updated)
        return updated

    async def list_for_user(self, user_id: uuid.UUID) -> list[CV]:
        """Returns all CVs for a user, ordered by default first, then by date."""
        result = await self.db.execute(
            select(CV)
            .where(CV.user_id == user_id)
            .order_by(CV.is_default.desc(), CV.created_at.desc())
        )
        return list(result.scalars().all())

    async def paginated_list_for_user(self, user_id: uuid.UUID, page: int, page_size: int,search:str = None) :
        pass

    async def get_default_for_user(self, user_id: uuid.UUID) -> CV | None:
        """Returns the user's default CV, or None if none is marked as default."""
        result = await self.db.execute(
            select(CV).where(
                and_(CV.user_id == user_id, CV.is_default == True)  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def set_default(self, user_id: uuid.UUID, cv_id: uuid.UUID) -> None:
        """
        Sets a CV as the user's default, unsets all others.
        Runs in two queries within the current transaction.
        """
        # Unset all defaults for this user
        await self.db.execute(
            update(CV)
            .where(CV.user_id == user_id)
            .values(is_default=False)
        )
        # Set the new default
        await self.db.execute(
            update(CV)
            .where(and_(CV.id == cv_id, CV.user_id == user_id))
            .values(is_default=True)
        )
        await self.db.flush()

    async def get_by_user_and_id(
        self, user_id: uuid.UUID, cv_id: uuid.UUID
    ) -> CV | None:
        """Fetches a CV only if it belongs to the specified user."""
        result = await self.db.execute(
            select(CV).where(
                and_(CV.id == cv_id, CV.user_id == user_id)
            )
        )
        return result.scalar_one_or_none()


    async def delete_cv(self, cv_id: uuid.UUID) -> None:
        """
        Delete CV for a user.
        """
        cv = await self.get_by_id(cv_id)
        if cv is None:
            raise NotFoundError(resource="CV", resource_id=str(cv_id))
        await self.delete(cv)
        await self.db.flush()
        await self.db.commit()
     

    async def remove_all_user_cvs(self, user_id: uuid.UUID) -> None:
        """
        Remove all CVs for a user.
        """
        await self.db.execute(
            delete(CV).where(CV.user_id == user_id)
        )
        await self.db.flush()
        await self.db.commit()
            
     
