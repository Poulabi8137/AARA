from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base
from app.core.exceptions import NotFoundError

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    def __init__(self, model: type[ModelT]) -> None:
        self._model = model

    async def create(self, db: AsyncSession, **kwargs: Any) -> ModelT:
        instance = self._model(**kwargs)
        db.add(instance)
        await db.flush()
        return instance

    async def get(self, db: AsyncSession, id: str) -> ModelT:
        col = self._model.id  # type: ignore[attr-defined]
        stmt = select(self._model).where(col == id)
        result = await db.execute(stmt)
        instance = result.scalar_one_or_none()
        if instance is None:
            raise NotFoundError(self._model.__name__, id)
        return instance

    async def get_many(
        self, db: AsyncSession, skip: int = 0, limit: int = 100, **filters: Any
    ) -> list[ModelT]:
        stmt = select(self._model)
        for key, value in filters.items():
            if hasattr(self._model, key):
                stmt = stmt.where(getattr(self._model, key) == value)
        stmt = stmt.offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def update(self, db: AsyncSession, id: str, **kwargs: Any) -> ModelT:
        col = self._model.id  # type: ignore[attr-defined]
        stmt = (
            update(self._model)
            .where(col == id)
            .values(**kwargs)
            .returning(self._model)
        )
        result = await db.execute(stmt)
        instance = result.scalar_one_or_none()
        if instance is None:
            raise NotFoundError(self._model.__name__, id)
        return instance

    async def delete(self, db: AsyncSession, id: str) -> None:
        col = self._model.id  # type: ignore[attr-defined]
        stmt = delete(self._model).where(col == id)
        await db.execute(stmt)

    async def count(self, db: AsyncSession, **filters: Any) -> int:
        stmt = select(func.count()).select_from(self._model)
        for key, value in filters.items():
            if hasattr(self._model, key):
                stmt = stmt.where(getattr(self._model, key) == value)
        result = await db.execute(stmt)
        return result.scalar_one()

    async def exists(self, db: AsyncSession, id: str) -> bool:
        try:
            await self.get(db, id)
            return True
        except NotFoundError:
            return False


class UnitOfWork:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def commit(self) -> None:
        await self._db.commit()

    async def rollback(self) -> None:
        await self._db.rollback()

    async def flush(self) -> None:
        await self._db.flush()
