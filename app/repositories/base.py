"""
Generic base repository with common CRUD operations.

All domain repositories inherit from this class to avoid code duplication.
"""

import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models.base import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType]):
    """
    Generic async repository providing standard CRUD operations.

    Type parameter ModelType must be a SQLAlchemy ORM model
    that inherits from BaseModel.
    """

    def __init__(self, model: type[ModelType], db: AsyncSession) -> None:
        self.model = model
        self.db = db

    async def get_by_id(self, entity_id: uuid.UUID) -> ModelType | None:
        """Fetches an entity by its UUID primary key. Returns None if not found."""
        result = await self.db.execute(
            select(self.model).where(self.model.id == entity_id)  # type: ignore[attr-defined]
        )
        return result.scalar_one_or_none()

    async def get_by_id_or_raise(self, entity_id: uuid.UUID) -> ModelType:
        """
        Fetches an entity by UUID. Raises NotFoundError if not found.

        Args:
            entity_id: UUID of the entity to fetch.

        Returns:
            The found entity.

        Raises:
            NotFoundError: Entity does not exist.
        """
        entity = await self.get_by_id(entity_id)
        if entity is None:
            raise NotFoundError(
                resource=self.model.__name__,
                resource_id=str(entity_id),
            )
        return entity

    async def list_all(
        self,
        *,
        filters: list[Any] | None = None,
        order_by: Any = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ModelType], int]:
        """
        Returns a paginated list of entities with total count.

        Args:
            filters:  SQLAlchemy WHERE clauses.
            order_by: SQLAlchemy ORDER BY clause.
            offset:   Number of records to skip.
            limit:    Maximum number of records to return.

        Returns:
            Tuple of (items, total_count).
        """
        query = select(self.model)
        count_query = select(func.count()).select_from(self.model)

        if filters:
            for f in filters:
                query = query.where(f)
                count_query = count_query.where(f)

        if order_by is not None:
            query = query.order_by(order_by)

        query = query.offset(offset).limit(limit)

        items_result = await self.db.execute(query)
        count_result = await self.db.execute(count_query)

        return list(items_result.scalars().all()), count_result.scalar_one()

    async def create(self, **kwargs: Any) -> ModelType:
        """Creates a new entity from keyword arguments."""
        entity = self.model(**kwargs)
        self.db.add(entity)
        await self.db.flush()
        await self.db.refresh(entity)
        return entity

    async def update(self, entity: ModelType, **kwargs: Any) -> ModelType:
        """Updates an existing entity with the provided fields."""
        for key, value in kwargs.items():
            if hasattr(entity, key) and value is not None:
                setattr(entity, key, value)
        await self.db.flush()
        await self.db.refresh(entity)
        return entity

    async def delete(self, entity: ModelType) -> None:
        """Deletes an entity from the database."""
        await self.db.delete(entity)
        await self.db.flush()

    async def delete_by_id(self, entity_id: uuid.UUID) -> None:
        """Deletes an entity by ID. Raises NotFoundError if not found."""
        entity = await self.get_by_id_or_raise(entity_id)
        await self.delete(entity)
