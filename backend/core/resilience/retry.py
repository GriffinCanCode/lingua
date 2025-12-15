"""Retry Policies with Exponential Backoff and Jitter

Implements configurable retry strategies for transient failures.
Supports multiple backoff algorithms and retry conditions.
"""
from __future__ import annotations

import asyncio
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Awaitable, Callable, Generic, TypeVar

from core.errors import (
    AppError,
    ErrorCode,
    Err,
    Ok,
    Result,
    timeout_error,
)

T = TypeVar("T")


class BackoffStrategy(Enum):
    """Available backoff strategies."""
    CONSTANT = auto()           # Fixed delay between retries
    LINEAR = auto()             # Linearly increasing delay
    EXPONENTIAL = auto()        # Exponentially increasing delay
    EXPONENTIAL_JITTER = auto() # Exponential with random jitter
    DECORRELATED_JITTER = auto() # AWS-style decorrelated jitter


@dataclass(frozen=True)
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL_JITTER
    jitter_factor: float = 0.5  # 0-1, portion of delay that can be jitter
    multiplier: float = 2.0     # Multiplier for exponential backoff
    retryable_codes: frozenset[ErrorCode] = field(
        default_factory=lambda: frozenset({
            # Network transient errors
            ErrorCode.E1000_NETWORK_GENERIC,
            ErrorCode.E1001_CONNECTION_REFUSED,
            ErrorCode.E1002_TIMEOUT,
            ErrorCode.E1010_EXTERNAL_SERVICE_UNAVAILABLE,
            ErrorCode.E1011_EXTERNAL_SERVICE_ERROR,
            ErrorCode.E1013_RATE_LIMITED,
            ErrorCode.E1021_HTTP_SERVER_ERROR,
            # Database transient errors
            ErrorCode.E4001_CONNECTION_FAILED,
            ErrorCode.E4003_TRANSACTION_FAILED,
            ErrorCode.E4004_DEADLOCK,
        })
    )
    non_retryable_codes: frozenset[ErrorCode] = field(
        default_factory=lambda: frozenset({
            # Validation errors - never retry
            ErrorCode.E2000_VALIDATION_GENERIC,
            ErrorCode.E2001_REQUIRED_FIELD_MISSING,
            ErrorCode.E2002_INVALID_FORMAT,
            # Auth errors - never retry
            ErrorCode.E3001_INVALID_CREDENTIALS,
            ErrorCode.E3003_TOKEN_INVALID,
            # Business logic errors - never retry
            ErrorCode.E4010_NOT_FOUND,
            ErrorCode.E4011_DUPLICATE_KEY,
            ErrorCode.E5001_OPERATION_NOT_ALLOWED,
        })
    )


@dataclass
class RetryAttempt:
    """Information about a single retry attempt."""
    attempt_number: int
    started_at: datetime
    delay_seconds: float
    error: AppError | None = None


@dataclass
class RetryResult(Generic[T]):
    """Result of a retry operation with full attempt history."""
    result: Result[T, AppError]
    attempts: list[RetryAttempt]
    total_duration_seconds: float
    
    @property
    def succeeded(self) -> bool:
        return self.result.is_ok()
    
    @property
    def attempt_count(self) -> int:
        return len(self.attempts)


class BackoffCalculator(ABC):
    """Abstract base for backoff delay calculation."""
    
    @abstractmethod
    def calculate(self, attempt: int, config: RetryConfig) -> float:
        """Calculate delay in seconds for given attempt number (1-indexed)."""
        pass


class ConstantBackoff(BackoffCalculator):
    def calculate(self, attempt: int, config: RetryConfig) -> float:
        return min(config.base_delay_seconds, config.max_delay_seconds)


class LinearBackoff(BackoffCalculator):
    def calculate(self, attempt: int, config: RetryConfig) -> float:
        delay = config.base_delay_seconds * attempt
        return min(delay, config.max_delay_seconds)


class ExponentialBackoff(BackoffCalculator):
    def calculate(self, attempt: int, config: RetryConfig) -> float:
        delay = config.base_delay_seconds * (config.multiplier ** (attempt - 1))
        return min(delay, config.max_delay_seconds)


class ExponentialJitterBackoff(BackoffCalculator):
    """Exponential backoff with equal jitter (±jitter_factor/2)."""
    
    def calculate(self, attempt: int, config: RetryConfig) -> float:
        base = config.base_delay_seconds * (config.multiplier ** (attempt - 1))
        base = min(base, config.max_delay_seconds)
        
        # Add jitter: base ± (base * jitter_factor / 2)
        jitter_range = base * config.jitter_factor
        jitter = random.uniform(-jitter_range / 2, jitter_range / 2)
        
        return max(0, min(base + jitter, config.max_delay_seconds))


class DecorrelatedJitterBackoff(BackoffCalculator):
    """AWS-style decorrelated jitter for optimal retry distribution.
    
    Formula: sleep = min(cap, random(base, sleep * 3))
    """
    
    def __init__(self):
        self._last_delay: float | None = None
    
    def calculate(self, attempt: int, config: RetryConfig) -> float:
        if attempt == 1 or self._last_delay is None:
            self._last_delay = config.base_delay_seconds
        else:
            self._last_delay = random.uniform(
                config.base_delay_seconds,
                self._last_delay * 3,
            )
        
        return min(self._last_delay, config.max_delay_seconds)


def get_backoff_calculator(strategy: BackoffStrategy) -> BackoffCalculator:
    """Factory for backoff calculators."""
    calculators: dict[BackoffStrategy, BackoffCalculator] = {
        BackoffStrategy.CONSTANT: ConstantBackoff(),
        BackoffStrategy.LINEAR: LinearBackoff(),
        BackoffStrategy.EXPONENTIAL: ExponentialBackoff(),
        BackoffStrategy.EXPONENTIAL_JITTER: ExponentialJitterBackoff(),
        BackoffStrategy.DECORRELATED_JITTER: DecorrelatedJitterBackoff(),
    }
    return calculators[strategy]


class RetryPolicy(Generic[T]):
    """Configurable retry policy for operations that may fail transiently.
    
    Usage:
        policy = RetryPolicy(RetryConfig(max_attempts=3))
        
        async def fetch_data():
            return await external_api.get_data()
        
        result = await policy.execute(fetch_data)
        match result.result:
            case Ok(data):
                process(data)
            case Err(error):
                log.error(f"Failed after {result.attempt_count} attempts")
    """
    
    def __init__(self, config: RetryConfig | None = None):
        self.config = config or RetryConfig()
        self._calculator = get_backoff_calculator(self.config.strategy)

    def should_retry(self, error: AppError, attempt: int) -> bool:
        """Determine if retry should be attempted."""
        if attempt >= self.config.max_attempts:
            return False
        
        # Never retry non-retryable codes
        if error.code in self.config.non_retryable_codes:
            return False
        
        # Always retry explicitly retryable codes
        if error.code in self.config.retryable_codes:
            return True
        
        # Default: don't retry unknown error codes
        return False

    async def execute(
        self,
        fn: Callable[[], Awaitable[Result[T, AppError]]],
        on_retry: Callable[[int, AppError, float], Awaitable[None]] | None = None,
    ) -> RetryResult[T]:
        """Execute function with retry policy.
        
        Args:
            fn: Async function returning Result
            on_retry: Optional callback before each retry (attempt, error, delay)
        
        Returns:
            RetryResult with final result and attempt history
        """
        attempts: list[RetryAttempt] = []
        start_time = datetime.now(timezone.utc)
        
        for attempt in range(1, self.config.max_attempts + 1):
            attempt_start = datetime.now(timezone.utc)
            delay = self._calculator.calculate(attempt, self.config)
            
            try:
                result = await fn()
            except Exception as e:
                # Convert exception to error
                result = Err(AppError(
                    code=ErrorCode.E9001_UNEXPECTED_ERROR,
                    message=str(e),
                ).chain(e))
            
            match result:
                case Ok(_):
                    attempts.append(RetryAttempt(
                        attempt_number=attempt,
                        started_at=attempt_start,
                        delay_seconds=delay,
                        error=None,
                    ))
                    end_time = datetime.now(timezone.utc)
                    return RetryResult(
                        result=result,
                        attempts=attempts,
                        total_duration_seconds=(end_time - start_time).total_seconds(),
                    )
                
                case Err(error):
                    attempts.append(RetryAttempt(
                        attempt_number=attempt,
                        started_at=attempt_start,
                        delay_seconds=delay,
                        error=error,
                    ))
                    
                    if not self.should_retry(error, attempt):
                        end_time = datetime.now(timezone.utc)
                        return RetryResult(
                            result=result,
                            attempts=attempts,
                            total_duration_seconds=(end_time - start_time).total_seconds(),
                        )
                    
                    # Call retry callback if provided
                    if on_retry:
                        await on_retry(attempt, error, delay)
                    
                    # Wait before retry
                    await asyncio.sleep(delay)
        
        # Should not reach here, but satisfy type checker
        end_time = datetime.now(timezone.utc)
        return RetryResult(
            result=Err(AppError(
                code=ErrorCode.E9001_UNEXPECTED_ERROR,
                message="Retry policy exhausted",
            )),
            attempts=attempts,
            total_duration_seconds=(end_time - start_time).total_seconds(),
        )


class TimeoutPolicy(Generic[T]):
    """Timeout wrapper for async operations.
    
    Usage:
        policy = TimeoutPolicy(timeout_seconds=5.0)
        result = await policy.execute(slow_operation)
    """
    
    def __init__(self, timeout_seconds: float, operation_name: str = "operation"):
        self.timeout_seconds = timeout_seconds
        self.operation_name = operation_name

    async def execute(
        self,
        fn: Callable[[], Awaitable[Result[T, AppError]]],
    ) -> Result[T, AppError]:
        """Execute function with timeout."""
        try:
            return await asyncio.wait_for(fn(), timeout=self.timeout_seconds)
        except asyncio.TimeoutError:
            return timeout_error(
                self.operation_name,
                self.timeout_seconds,
                origin="timeout_policy",
            )


class CombinedPolicy(Generic[T]):
    """Combines timeout and retry policies.
    
    Each retry attempt has its own timeout. Total time = max_attempts * timeout.
    """
    
    def __init__(
        self,
        timeout_seconds: float,
        retry_config: RetryConfig | None = None,
        operation_name: str = "operation",
    ):
        self.timeout = TimeoutPolicy[T](timeout_seconds, operation_name)
        self.retry = RetryPolicy[T](retry_config)

    async def execute(
        self,
        fn: Callable[[], Awaitable[Result[T, AppError]]],
        on_retry: Callable[[int, AppError, float], Awaitable[None]] | None = None,
    ) -> RetryResult[T]:
        """Execute function with timeout per attempt and retry policy."""
        async def timed_fn() -> Result[T, AppError]:
            return await self.timeout.execute(fn)
        
        return await self.retry.execute(timed_fn, on_retry)


# Decorator for retryable functions
def retryable(config: RetryConfig | None = None):
    """Decorator to make async function retryable.
    
    Usage:
        @retryable(RetryConfig(max_attempts=3))
        async def fetch_data() -> Result[Data, AppError]:
            ...
    """
    def decorator(fn: Callable[..., Awaitable[Result[T, AppError]]]):
        policy = RetryPolicy[T](config)
        
        async def wrapper(*args, **kwargs) -> Result[T, AppError]:
            result = await policy.execute(lambda: fn(*args, **kwargs))
            return result.result
        
        return wrapper
    return decorator


def with_timeout(timeout_seconds: float, operation_name: str = "operation"):
    """Decorator to add timeout to async function.
    
    Usage:
        @with_timeout(5.0, "external_api_call")
        async def call_api() -> Result[Response, AppError]:
            ...
    """
    def decorator(fn: Callable[..., Awaitable[Result[T, AppError]]]):
        policy = TimeoutPolicy[T](timeout_seconds, operation_name)
        
        async def wrapper(*args, **kwargs) -> Result[T, AppError]:
            return await policy.execute(lambda: fn(*args, **kwargs))
        
        return wrapper
    return decorator

