"""Error Boundary Mappers

Provides module boundary error mapping for clean error propagation.
Each module should have a single error type at its boundary, with
internal errors mapped at the boundary.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Awaitable, Callable, Generic, TypeVar

from sqlalchemy.exc import (
    DBAPIError,
    IntegrityError,
    OperationalError,
    SQLAlchemyError,
)

from .types import (
    AppError,
    ErrorCode,
    ErrorContext,
    Err,
    Ok,
    Result,
)
from .builders import (
    db_connection_failed,
    duplicate_key,
    foreign_key_violation,
    internal_error,
    not_found,
    timeout_error,
    token_expired,
    token_invalid,
    transaction_failed,
    validation_error,
)

T = TypeVar("T")


class ErrorMapper(ABC, Generic[T]):
    """Abstract base for error mappers at module boundaries."""
    
    @abstractmethod
    def map_error(self, error: AppError) -> AppError:
        """Map internal error to boundary error."""
        pass
    
    def map_result(self, result: Result[T, AppError]) -> Result[T, AppError]:
        """Map errors in Result while preserving success values."""
        match result:
            case Ok(_):
                return result
            case Err(e):
                return Err(self.map_error(e))


class DatabaseErrorMapper(ErrorMapper[T]):
    """Maps database-layer errors to clean API errors.
    
    Handles SQLAlchemy exceptions and maps them to appropriate
    application error codes.
    """
    
    def __init__(self, origin: str = "database"):
        self.origin = origin

    def map_error(self, error: AppError) -> AppError:
        """Map database error, preserving context."""
        # If already mapped, return as-is
        if 4000 <= error.code.value < 5000:
            return error
        
        # Add origin context
        return error.with_context(origin=self.origin)

    def map_exception(self, exc: Exception) -> AppError:
        """Map SQLAlchemy exception to AppError."""
        if isinstance(exc, IntegrityError):
            return self._map_integrity_error(exc)
        if isinstance(exc, OperationalError):
            return self._map_operational_error(exc)
        if isinstance(exc, SQLAlchemyError):
            return transaction_failed(str(exc), origin=self.origin).error
        
        return internal_error(
            f"Database error: {exc}",
            origin=self.origin,
            cause=exc,
        ).error

    def _map_integrity_error(self, exc: IntegrityError) -> AppError:
        """Map integrity constraint violations."""
        message = str(exc.orig) if exc.orig else str(exc)
        
        # Detect duplicate key
        if "duplicate key" in message.lower() or "unique constraint" in message.lower():
            return duplicate_key(
                entity="record",
                field="unknown",
                value="unknown",
                origin=self.origin,
            ).error
        
        # Detect foreign key violation
        if "foreign key" in message.lower():
            return foreign_key_violation(
                entity="record",
                reference="unknown",
                origin=self.origin,
            ).error
        
        # Generic constraint violation
        return AppError(
            code=ErrorCode.E4013_CHECK_CONSTRAINT,
            message=f"Constraint violation: {message}",
            context=ErrorContext(origin=self.origin),
            cause=exc,
        )

    def _map_operational_error(self, exc: OperationalError) -> AppError:
        """Map operational/connection errors."""
        message = str(exc.orig) if exc.orig else str(exc)
        
        if "timeout" in message.lower():
            return timeout_error(
                "database query",
                30.0,  # Default timeout assumption
                origin=self.origin,
            ).error
        
        if "connection" in message.lower() or "connect" in message.lower():
            return db_connection_failed(message, origin=self.origin).error
        
        return transaction_failed(message, origin=self.origin).error


class AuthErrorMapper(ErrorMapper[T]):
    """Maps authentication errors to clean API errors."""
    
    def __init__(self, origin: str = "auth"):
        self.origin = origin

    def map_error(self, error: AppError) -> AppError:
        """Map auth error, preserving context."""
        if 3000 <= error.code.value < 4000:
            return error
        return error.with_context(origin=self.origin)

    def map_exception(self, exc: Exception) -> AppError:
        """Map auth-related exceptions."""
        from jose import ExpiredSignatureError, JWTError
        
        if isinstance(exc, ExpiredSignatureError):
            return token_expired(origin=self.origin).error
        if isinstance(exc, JWTError):
            return token_invalid(str(exc), origin=self.origin).error
        
        return internal_error(
            f"Authentication error: {exc}",
            origin=self.origin,
            cause=exc,
        ).error


class ValidationErrorMapper(ErrorMapper[T]):
    """Maps validation errors to clean API errors."""
    
    def __init__(self, origin: str = "validation"):
        self.origin = origin

    def map_error(self, error: AppError) -> AppError:
        """Map validation error."""
        if 2000 <= error.code.value < 3000:
            return error
        return error.with_context(origin=self.origin)

    def map_pydantic_errors(self, errors: list[dict]) -> list[AppError]:
        """Map Pydantic validation errors to AppErrors."""
        result = []
        for err in errors:
            field = ".".join(str(loc) for loc in err.get("loc", []))
            msg = err.get("msg", "Validation error")
            err_type = err.get("type", "value_error")
            
            code = ErrorCode.E2000_VALIDATION_GENERIC
            if err_type == "value_error.missing":
                code = ErrorCode.E2001_REQUIRED_FIELD_MISSING
            elif "type_error" in err_type:
                code = ErrorCode.E2004_INVALID_TYPE
            elif "value_error" in err_type:
                code = ErrorCode.E2002_INVALID_FORMAT
            
            result.append(AppError(
                code=code,
                message=f"{field}: {msg}",
                context=ErrorContext(origin=self.origin),
                metadata={"field": field, "error_type": err_type},
            ))
        
        return result


class EngineErrorMapper(ErrorMapper[T]):
    """Maps engine/business logic errors to API errors."""
    
    def __init__(self, engine_name: str):
        self.engine_name = engine_name
        self.origin = f"engine.{engine_name}"

    def map_error(self, error: AppError) -> AppError:
        """Map engine error with origin context."""
        return error.with_context(origin=self.origin)

    def map_exception(self, exc: Exception) -> AppError:
        """Map engine exceptions to errors."""
        return internal_error(
            f"Engine error in {self.engine_name}: {exc}",
            origin=self.origin,
            cause=exc,
        ).error


# Decorator for automatic error mapping at boundaries
def map_errors(mapper: ErrorMapper[T]):
    """Decorator to map errors at function boundaries.
    
    Usage:
        @map_errors(DatabaseErrorMapper("user_repository"))
        async def get_user(user_id: str) -> Result[User, AppError]:
            ...
    """
    def decorator(fn: Callable[..., Awaitable[Result[T, AppError]]]):
        async def wrapper(*args, **kwargs) -> Result[T, AppError]:
            try:
                result = await fn(*args, **kwargs)
                return mapper.map_result(result)
            except Exception as e:
                if hasattr(mapper, "map_exception"):
                    return Err(mapper.map_exception(e))
                raise
        return wrapper
    return decorator


def map_db_errors(origin: str = "database"):
    """Convenience decorator for database error mapping.
    
    Usage:
        @map_db_errors("user_repository")
        async def find_user(user_id: UUID) -> Result[User, AppError]:
            ...
    """
    return map_errors(DatabaseErrorMapper(origin))


def map_auth_errors(origin: str = "auth"):
    """Convenience decorator for auth error mapping."""
    return map_errors(AuthErrorMapper(origin))

