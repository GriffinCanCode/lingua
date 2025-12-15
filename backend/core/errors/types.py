"""Monadic Error Handling Types

Implements Result/Either types with Haskell-grade rigor for deterministic,
composable error propagation. Uses Python's type system to enforce exhaustive
matching at type-check time.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import (
    TYPE_CHECKING, Callable, Generic, Iterator, NoReturn, 
    TypeVar, Union, final, overload,
)
from uuid import uuid4

if TYPE_CHECKING:
    from collections.abc import Awaitable

T = TypeVar("T")
U = TypeVar("U")
E = TypeVar("E", bound="AppError")
F = TypeVar("F", bound="AppError")


class ErrorCode(Enum):
    """Hierarchical error code taxonomy.
    
    E1xxx: Network/External service failures
    E2xxx: Validation errors
    E3xxx: Authentication/Authorization errors
    E4xxx: Database errors
    E5xxx: Business logic errors
    E6xxx: Resource errors
    E9xxx: Internal/Unknown errors
    """
    # Network/External (E1xxx)
    E1000_NETWORK_GENERIC = 1000
    E1001_CONNECTION_REFUSED = 1001
    E1002_TIMEOUT = 1002
    E1003_DNS_FAILURE = 1003
    E1004_SSL_ERROR = 1004
    E1010_EXTERNAL_SERVICE_UNAVAILABLE = 1010
    E1011_EXTERNAL_SERVICE_ERROR = 1011
    E1012_CIRCUIT_OPEN = 1012
    E1013_RATE_LIMITED = 1013
    E1020_HTTP_CLIENT_ERROR = 1020
    E1021_HTTP_SERVER_ERROR = 1021
    
    # Validation (E2xxx)
    E2000_VALIDATION_GENERIC = 2000
    E2001_REQUIRED_FIELD_MISSING = 2001
    E2002_INVALID_FORMAT = 2002
    E2003_OUT_OF_RANGE = 2003
    E2004_INVALID_TYPE = 2004
    E2005_CONSTRAINT_VIOLATION = 2005
    E2010_INVALID_EMAIL = 2010
    E2011_INVALID_UUID = 2011
    E2012_INVALID_DATE = 2012
    E2020_PAYLOAD_TOO_LARGE = 2020
    E2021_INVALID_JSON = 2021
    
    # Authentication/Authorization (E3xxx)
    E3000_AUTH_GENERIC = 3000
    E3001_INVALID_CREDENTIALS = 3001
    E3002_TOKEN_EXPIRED = 3002
    E3003_TOKEN_INVALID = 3003
    E3004_TOKEN_MISSING = 3004
    E3010_INSUFFICIENT_PERMISSIONS = 3010
    E3011_RESOURCE_FORBIDDEN = 3011
    E3020_ACCOUNT_DISABLED = 3020
    E3021_ACCOUNT_LOCKED = 3021
    E3022_SESSION_EXPIRED = 3022
    
    # Database (E4xxx)
    E4000_DATABASE_GENERIC = 4000
    E4001_CONNECTION_FAILED = 4001
    E4002_QUERY_FAILED = 4002
    E4003_TRANSACTION_FAILED = 4003
    E4004_DEADLOCK = 4004
    E4010_NOT_FOUND = 4010
    E4011_DUPLICATE_KEY = 4011
    E4012_FOREIGN_KEY_VIOLATION = 4012
    E4013_CHECK_CONSTRAINT = 4013
    E4020_MIGRATION_FAILED = 4020
    E4021_SCHEMA_MISMATCH = 4021
    
    # Business Logic (E5xxx)
    E5000_BUSINESS_GENERIC = 5000
    E5001_OPERATION_NOT_ALLOWED = 5001
    E5002_STATE_CONFLICT = 5002
    E5003_PRECONDITION_FAILED = 5003
    E5004_INVARIANT_VIOLATED = 5004
    E5010_QUOTA_EXCEEDED = 5010
    E5011_LIMIT_REACHED = 5011
    E5020_DEPENDENCY_ERROR = 5020
    
    # Resource (E6xxx)
    E6000_RESOURCE_GENERIC = 6000
    E6001_FILE_NOT_FOUND = 6001
    E6002_FILE_READ_ERROR = 6002
    E6003_FILE_WRITE_ERROR = 6003
    E6010_MEMORY_EXHAUSTED = 6010
    E6011_DISK_FULL = 6011
    
    # Internal (E9xxx)
    E9000_INTERNAL_GENERIC = 9000
    E9001_UNEXPECTED_ERROR = 9001
    E9002_NOT_IMPLEMENTED = 9002
    E9003_ASSERTION_FAILED = 9003

    @property
    def http_status(self) -> int:
        """Map error code to appropriate HTTP status."""
        code = self.value
        if 1000 <= code < 1100:
            return 502 if code in (1010, 1011) else 503
        if 2000 <= code < 2100:
            return 400
        if 3000 <= code < 3010:
            return 401
        if 3010 <= code < 3100:
            return 403
        if code == 4010:
            return 404
        if 4011 <= code < 4020:
            return 409
        if 4000 <= code < 4100:
            return 503
        if 5000 <= code < 5010:
            return 409
        if 5010 <= code < 5100:
            return 429
        if 6000 <= code < 6100:
            return 500
        return 500

    @property
    def category(self) -> str:
        """Human-readable error category."""
        code = self.value
        if 1000 <= code < 2000:
            return "network"
        if 2000 <= code < 3000:
            return "validation"
        if 3000 <= code < 4000:
            return "auth"
        if 4000 <= code < 5000:
            return "database"
        if 5000 <= code < 6000:
            return "business"
        if 6000 <= code < 7000:
            return "resource"
        return "internal"


@dataclass(frozen=True, slots=True)
class ErrorContext:
    """Immutable context for error tracing and debugging."""
    correlation_id: str = field(default_factory=lambda: str(uuid4())[:8])
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    origin: str = ""
    trace_id: str | None = None
    span_id: str | None = None
    user_id: str | None = None
    request_id: str | None = None

    def with_origin(self, origin: str) -> ErrorContext:
        return ErrorContext(
            correlation_id=self.correlation_id,
            timestamp=self.timestamp,
            origin=origin,
            trace_id=self.trace_id,
            span_id=self.span_id,
            user_id=self.user_id,
            request_id=self.request_id,
        )


@dataclass(frozen=True, slots=True)
class AppError:
    """Base application error with full context.
    
    All errors carry:
    - Typed error code from taxonomy
    - Human-readable message
    - Structured metadata for debugging
    - Full tracing context
    - Optional cause for error chaining
    """
    code: ErrorCode
    message: str
    context: ErrorContext = field(default_factory=ErrorContext)
    metadata: dict = field(default_factory=dict)
    cause: Exception | None = None
    
    @property
    def error_id(self) -> str:
        """Unique identifier for this error instance."""
        return f"{self.code.name}:{self.context.correlation_id}"
    
    def with_context(self, **kwargs) -> AppError:
        """Create new error with updated context."""
        new_ctx = ErrorContext(
            correlation_id=kwargs.get("correlation_id", self.context.correlation_id),
            timestamp=self.context.timestamp,
            origin=kwargs.get("origin", self.context.origin),
            trace_id=kwargs.get("trace_id", self.context.trace_id),
            span_id=kwargs.get("span_id", self.context.span_id),
            user_id=kwargs.get("user_id", self.context.user_id),
            request_id=kwargs.get("request_id", self.context.request_id),
        )
        return AppError(
            code=self.code,
            message=self.message,
            context=new_ctx,
            metadata={**self.metadata, **kwargs.get("metadata", {})},
            cause=self.cause,
        )

    def with_metadata(self, **kwargs) -> AppError:
        """Create new error with additional metadata."""
        return AppError(
            code=self.code,
            message=self.message,
            context=self.context,
            metadata={**self.metadata, **kwargs},
            cause=self.cause,
        )

    def chain(self, cause: Exception) -> AppError:
        """Chain this error with a cause."""
        return AppError(
            code=self.code,
            message=self.message,
            context=self.context,
            metadata=self.metadata,
            cause=cause,
        )
    
    def to_dict(self) -> dict:
        """Serialize error for API responses."""
        return {
            "error": {
                "code": self.code.name,
                "code_num": self.code.value,
                "message": self.message,
                "category": self.code.category,
                "correlation_id": self.context.correlation_id,
                "timestamp": self.context.timestamp.isoformat(),
                "metadata": self.metadata,
            }
        }

    def __str__(self) -> str:
        return f"[{self.code.name}] {self.message} (correlation_id={self.context.correlation_id})"


@final
@dataclass(frozen=True, slots=True)
class Ok(Generic[T]):
    """Success variant of Result monad.
    
    Wraps a successful value. Immutable and hashable when T is hashable.
    """
    value: T
    
    def is_ok(self) -> bool:
        return True
    
    def is_err(self) -> bool:
        return False

    def unwrap(self) -> T:
        """Extract the value. Safe because Ok always contains a value."""
        return self.value
    
    def unwrap_or(self, default: T) -> T:
        return self.value
    
    def unwrap_or_else(self, f: Callable[[AppError], T]) -> T:
        return self.value
    
    def expect(self, msg: str) -> T:
        return self.value
    
    def map(self, f: Callable[[T], U]) -> Result[U, AppError]:
        """Transform the success value."""
        return Ok(f(self.value))
    
    def map_err(self, f: Callable[[AppError], F]) -> Result[T, F]:
        """No-op for Ok variant."""
        return self  # type: ignore
    
    def flat_map(self, f: Callable[[T], Result[U, AppError]]) -> Result[U, AppError]:
        """Chain operations that may fail."""
        return f(self.value)
    
    def and_then(self, f: Callable[[T], Result[U, AppError]]) -> Result[U, AppError]:
        """Alias for flat_map."""
        return f(self.value)
    
    def or_else(self, f: Callable[[AppError], Result[T, F]]) -> Result[T, F]:
        """No-op for Ok variant."""
        return self  # type: ignore
    
    def match(
        self,
        ok: Callable[[T], U],
        err: Callable[[AppError], U],
    ) -> U:
        """Pattern match on Result. Forces exhaustive handling."""
        return ok(self.value)

    async def map_async(self, f: Callable[[T], Awaitable[U]]) -> Result[U, AppError]:
        """Async variant of map."""
        return Ok(await f(self.value))

    async def flat_map_async(
        self, f: Callable[[T], Awaitable[Result[U, AppError]]]
    ) -> Result[U, AppError]:
        """Async variant of flat_map."""
        return await f(self.value)

    def __iter__(self) -> Iterator[T]:
        yield self.value


@final
@dataclass(frozen=True, slots=True)
class Err(Generic[E]):
    """Failure variant of Result monad.
    
    Wraps an AppError. Immutable and carries full error context.
    """
    error: E
    
    def is_ok(self) -> bool:
        return False
    
    def is_err(self) -> bool:
        return True

    def unwrap(self) -> NoReturn:
        """Raises because Err has no value to unwrap."""
        raise ValueError(f"Called unwrap on Err: {self.error}")
    
    def unwrap_or(self, default: T) -> T:
        return default
    
    def unwrap_or_else(self, f: Callable[[E], T]) -> T:
        return f(self.error)
    
    def unwrap_err(self) -> E:
        """Extract the error."""
        return self.error
    
    def expect(self, msg: str) -> NoReturn:
        raise ValueError(f"{msg}: {self.error}")
    
    def map(self, f: Callable[[T], U]) -> Result[U, E]:
        """No-op for Err variant."""
        return self  # type: ignore
    
    def map_err(self, f: Callable[[E], F]) -> Result[T, F]:
        """Transform the error."""
        return Err(f(self.error))
    
    def flat_map(self, f: Callable[[T], Result[U, E]]) -> Result[U, E]:
        """No-op for Err variant."""
        return self  # type: ignore
    
    def and_then(self, f: Callable[[T], Result[U, E]]) -> Result[U, E]:
        """No-op for Err variant."""
        return self  # type: ignore
    
    def or_else(self, f: Callable[[E], Result[T, F]]) -> Result[T, F]:
        """Try to recover from error."""
        return f(self.error)
    
    def match(
        self,
        ok: Callable[[T], U],
        err: Callable[[E], U],
    ) -> U:
        """Pattern match on Result. Forces exhaustive handling."""
        return err(self.error)

    async def map_async(self, f: Callable[[T], Awaitable[U]]) -> Result[U, E]:
        """No-op for Err variant."""
        return self  # type: ignore

    async def flat_map_async(
        self, f: Callable[[T], Awaitable[Result[U, E]]]
    ) -> Result[U, E]:
        """No-op for Err variant."""
        return self  # type: ignore

    def __iter__(self) -> Iterator:
        return iter([])


# Type alias for Result monad
Result = Union[Ok[T], Err[E]]


def ok(value: T) -> Ok[T]:
    """Construct Ok variant."""
    return Ok(value)


def err(error: E) -> Err[E]:
    """Construct Err variant."""
    return Err(error)


def from_exception(
    exc: Exception,
    code: ErrorCode = ErrorCode.E9001_UNEXPECTED_ERROR,
    message: str | None = None,
    origin: str = "",
    **metadata,
) -> Err[AppError]:
    """Convert exception to Err with full context."""
    return Err(AppError(
        code=code,
        message=message or str(exc),
        context=ErrorContext(origin=origin),
        metadata=metadata,
        cause=exc,
    ))


def try_result(
    f: Callable[[], T],
    code: ErrorCode = ErrorCode.E9001_UNEXPECTED_ERROR,
    origin: str = "",
) -> Result[T, AppError]:
    """Execute function and wrap result in Result monad.
    
    Catches exceptions and converts to Err.
    """
    try:
        return Ok(f())
    except Exception as e:
        return from_exception(e, code=code, origin=origin)


async def try_result_async(
    f: Callable[[], Awaitable[T]],
    code: ErrorCode = ErrorCode.E9001_UNEXPECTED_ERROR,
    origin: str = "",
) -> Result[T, AppError]:
    """Async variant of try_result."""
    try:
        return Ok(await f())
    except Exception as e:
        return from_exception(e, code=code, origin=origin)


def collect_results(results: list[Result[T, AppError]]) -> Result[list[T], list[AppError]]:
    """Collect list of Results into Result of list.
    
    Returns Ok with all values if all are Ok.
    Returns Err with all errors if any are Err.
    """
    values: list[T] = []
    errors: list[AppError] = []
    
    for r in results:
        match r:
            case Ok(v):
                values.append(v)
            case Err(e):
                errors.append(e)
    
    if errors:
        return Err(errors)  # type: ignore
    return Ok(values)


def sequence_results(results: list[Result[T, AppError]]) -> Result[list[T], AppError]:
    """Sequence Results, failing fast on first error.
    
    Returns Ok with all values if all are Ok.
    Returns first Err encountered.
    """
    values: list[T] = []
    
    for r in results:
        match r:
            case Ok(v):
                values.append(v)
            case Err(e):
                return Err(e)
    
    return Ok(values)


def ensure(
    condition: bool,
    error: AppError,
) -> Result[None, AppError]:
    """Guard function that returns Err if condition is False."""
    return Ok(None) if condition else Err(error)


def require(
    value: T | None,
    error: AppError,
) -> Result[T, AppError]:
    """Convert nullable to Result, returning Err if None."""
    return Ok(value) if value is not None else Err(error)

