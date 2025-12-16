"""Database Module with Monadic Error Handling

Provides async database session management and query helpers
with Result-based error propagation.
"""
from contextlib import asynccontextmanager
from typing import AsyncIterator, TypeVar
from uuid import UUID as PyUUID

from sqlalchemy import select, String
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from core.config import settings
from core.errors import (
    AppError,
    Ok,
    Err,
    Result,
    not_found,
    db_connection_failed,
    transaction_failed,
    DatabaseErrorMapper,
)

T = TypeVar("T")


class GUID(TypeDecorator):
    """Platform-agnostic GUID type.
    
    Uses PostgreSQL's UUID type when available, otherwise stores as CHAR(32).
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        if isinstance(value, PyUUID):
            return value.hex
        return PyUUID(value).hex

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, PyUUID):
            return value
        return PyUUID(value)

engine_kwargs = {
    "echo": settings.LOG_SQL,
}

if "sqlite" not in settings.DATABASE_URL:
    engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_size": 5,
        "max_overflow": 10,
    })

engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()

# Error mapper for database operations
_db_mapper = DatabaseErrorMapper("database")


async def get_db() -> AsyncIterator[AsyncSession]:
    """Dependency that yields database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Context manager for database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def fetch_one(
    session: AsyncSession,
    model: type[T],
    id: PyUUID,
    entity_name: str | None = None,
) -> Result[T, AppError]:
    """Fetch single entity by ID.
    
    Returns:
        Ok(entity) if found
        Err(not_found) if not found
        Err(db_error) on database failure
    """
    name = entity_name or model.__name__
    try:
        result = await session.execute(select(model).where(model.id == id))
        entity = result.scalar_one_or_none()
        if entity is None:
            return not_found(name, id, origin="database.fetch_one")
        return Ok(entity)
    except SQLAlchemyError as e:
        return Err(_db_mapper.map_exception(e))


async def fetch_one_by(
    session: AsyncSession,
    model: type[T],
    entity_name: str | None = None,
    **filters,
) -> Result[T, AppError]:
    """Fetch single entity by arbitrary filters.
    
    Returns:
        Ok(entity) if found
        Err(not_found) if not found
    """
    name = entity_name or model.__name__
    try:
        query = select(model)
        for key, value in filters.items():
            query = query.where(getattr(model, key) == value)
        result = await session.execute(query)
        entity = result.scalar_one_or_none()
        if entity is None:
            return not_found(name, origin="database.fetch_one_by")
        return Ok(entity)
    except SQLAlchemyError as e:
        return Err(_db_mapper.map_exception(e))


async def create_entity(
    session: AsyncSession,
    entity: T,
) -> Result[T, AppError]:
    """Create entity in database.
    
    Returns:
        Ok(entity) on success (with populated ID)
        Err(AppError) on failure
    """
    try:
        session.add(entity)
        await session.commit()
        await session.refresh(entity)
        return Ok(entity)
    except SQLAlchemyError as e:
        await session.rollback()
        return Err(_db_mapper.map_exception(e))


async def update_entity(
    session: AsyncSession,
    entity: T,
) -> Result[T, AppError]:
    """Update entity in database.
    
    Returns:
        Ok(entity) on success
        Err(AppError) on failure
    """
    try:
        await session.commit()
        await session.refresh(entity)
        return Ok(entity)
    except SQLAlchemyError as e:
        await session.rollback()
        return Err(_db_mapper.map_exception(e))


async def delete_entity(
    session: AsyncSession,
    entity: T,
) -> Result[None, AppError]:
    """Delete entity from database.
    
    Returns:
        Ok(None) on success
        Err(AppError) on failure
    """
    try:
        session.delete(entity)
        await session.commit()
        return Ok(None)
    except SQLAlchemyError as e:
        await session.rollback()
        return Err(_db_mapper.map_exception(e))


async def execute_transaction(
    session: AsyncSession,
    operations: list,
) -> Result[None, AppError]:
    """Execute multiple operations in a transaction.
    
    All operations succeed or all are rolled back.
    """
    try:
        for op in operations:
            await op
        await session.commit()
        return Ok(None)
    except SQLAlchemyError as e:
        await session.rollback()
        return Err(_db_mapper.map_exception(e))
