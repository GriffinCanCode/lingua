"""Circuit Breaker Pattern Implementation

Provides resilient external service calls with automatic failure detection,
state transitions, and recovery. Configurable thresholds and behavior.
"""
from __future__ import annotations

import asyncio
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
    circuit_open,
    external_service_unavailable,
)

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = auto()     # Normal operation, requests pass through
    OPEN = auto()       # Failing, requests rejected immediately
    HALF_OPEN = auto()  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5           # Failures before opening
    success_threshold: int = 2           # Successes in half-open before closing
    timeout_seconds: float = 30.0        # Time before transitioning open -> half-open
    half_open_max_calls: int = 3         # Max concurrent calls in half-open
    excluded_codes: frozenset[ErrorCode] = field(
        default_factory=lambda: frozenset({
            ErrorCode.E2000_VALIDATION_GENERIC,
            ErrorCode.E2001_REQUIRED_FIELD_MISSING,
            ErrorCode.E2002_INVALID_FORMAT,
            ErrorCode.E3001_INVALID_CREDENTIALS,
            ErrorCode.E4010_NOT_FOUND,
        })
    )


@dataclass
class CircuitStats:
    """Statistics for a circuit breaker."""
    state: CircuitState
    failure_count: int
    success_count: int
    last_failure: datetime | None
    last_success: datetime | None
    last_state_change: datetime
    total_requests: int
    total_failures: int
    total_successes: int


class CircuitBreaker(Generic[T]):
    """Circuit breaker for external service protection.
    
    Tracks failures and opens circuit when threshold exceeded.
    Automatically tests recovery after timeout period.
    
    Usage:
        breaker = CircuitBreaker("payment-service", config)
        
        async def call_payment():
            return await payment_api.charge(amount)
        
        result = await breaker.call(call_payment)
        match result:
            case Ok(response):
                process_payment(response)
            case Err(error):
                handle_error(error)
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig | None = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._last_failure: datetime | None = None
        self._last_success: datetime | None = None
        self._last_state_change = datetime.now(timezone.utc)
        self._total_requests = 0
        self._total_failures = 0
        self._total_successes = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def stats(self) -> CircuitStats:
        return CircuitStats(
            state=self._state,
            failure_count=self._failure_count,
            success_count=self._success_count,
            last_failure=self._last_failure,
            last_success=self._last_success,
            last_state_change=self._last_state_change,
            total_requests=self._total_requests,
            total_failures=self._total_failures,
            total_successes=self._total_successes,
        )

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _should_transition_to_half_open(self) -> bool:
        """Check if enough time has passed to try half-open."""
        if self._state != CircuitState.OPEN:
            return False
        elapsed = (self._now() - self._last_state_change).total_seconds()
        return elapsed >= self.config.timeout_seconds

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state."""
        self._state = new_state
        self._last_state_change = self._now()
        
        if new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._success_count = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._success_count = 0
            self._half_open_calls = 0
        elif new_state == CircuitState.OPEN:
            self._success_count = 0

    def _should_count_as_failure(self, error: AppError) -> bool:
        """Determine if this error should count towards failure threshold."""
        return error.code not in self.config.excluded_codes

    async def _record_success(self) -> None:
        """Record successful call."""
        async with self._lock:
            self._success_count += 1
            self._total_successes += 1
            self._last_success = self._now()
            
            if self._state == CircuitState.HALF_OPEN:
                if self._success_count >= self.config.success_threshold:
                    self._transition_to(CircuitState.CLOSED)

    async def _record_failure(self, error: AppError) -> None:
        """Record failed call."""
        if not self._should_count_as_failure(error):
            return
            
        async with self._lock:
            self._failure_count += 1
            self._total_failures += 1
            self._last_failure = self._now()
            
            if self._state == CircuitState.HALF_OPEN:
                self._transition_to(CircuitState.OPEN)
            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.config.failure_threshold:
                    self._transition_to(CircuitState.OPEN)

    async def _can_execute(self) -> Result[None, AppError]:
        """Check if request can proceed."""
        async with self._lock:
            self._total_requests += 1
            
            if self._state == CircuitState.CLOSED:
                return Ok(None)
            
            if self._state == CircuitState.OPEN:
                if self._should_transition_to_half_open():
                    self._transition_to(CircuitState.HALF_OPEN)
                else:
                    return circuit_open(self.name, origin="circuit_breaker")
            
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    return circuit_open(self.name, origin="circuit_breaker")
                self._half_open_calls += 1
            
            return Ok(None)

    async def call(
        self,
        fn: Callable[[], Awaitable[Result[T, AppError]]],
    ) -> Result[T, AppError]:
        """Execute function through circuit breaker.
        
        Returns the function result if circuit allows execution.
        Returns Err(circuit_open) if circuit is open.
        """
        # Check if we can execute
        can_exec = await self._can_execute()
        if can_exec.is_err():
            return can_exec  # type: ignore
        
        # Execute the function
        try:
            result = await fn()
        except Exception as e:
            # Convert exception to error and record failure
            error = AppError(
                code=ErrorCode.E1011_EXTERNAL_SERVICE_ERROR,
                message=str(e),
            ).chain(e)
            await self._record_failure(error)
            return Err(error)
        
        # Record result
        match result:
            case Ok(_):
                await self._record_success()
            case Err(error):
                await self._record_failure(error)
        
        return result

    async def call_with_fallback(
        self,
        fn: Callable[[], Awaitable[Result[T, AppError]]],
        fallback: Callable[[], Awaitable[T]],
    ) -> Result[T, AppError]:
        """Execute function with fallback when circuit is open."""
        result = await self.call(fn)
        
        if result.is_err() and result.unwrap_err().code == ErrorCode.E1012_CIRCUIT_OPEN:
            try:
                fallback_value = await fallback()
                return Ok(fallback_value)
            except Exception as e:
                return external_service_unavailable(
                    self.name,
                    f"Fallback also failed: {e}",
                    origin="circuit_breaker",
                )
        
        return result

    def reset(self) -> None:
        """Manually reset circuit to closed state."""
        self._transition_to(CircuitState.CLOSED)


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""
    
    _breakers: dict[str, CircuitBreaker] = {}
    _configs: dict[str, CircuitBreakerConfig] = {}
    _lock = asyncio.Lock()
    
    @classmethod
    def configure(cls, name: str, config: CircuitBreakerConfig) -> None:
        """Pre-configure a circuit breaker."""
        cls._configs[name] = config
    
    @classmethod
    async def get(cls, name: str) -> CircuitBreaker:
        """Get or create a circuit breaker by name."""
        async with cls._lock:
            if name not in cls._breakers:
                config = cls._configs.get(name)
                cls._breakers[name] = CircuitBreaker(name, config)
            return cls._breakers[name]
    
    @classmethod
    def get_sync(cls, name: str) -> CircuitBreaker:
        """Synchronous version for use in non-async contexts."""
        if name not in cls._breakers:
            config = cls._configs.get(name)
            cls._breakers[name] = CircuitBreaker(name, config)
        return cls._breakers[name]
    
    @classmethod
    def stats(cls) -> dict[str, CircuitStats]:
        """Get stats for all circuit breakers."""
        return {name: breaker.stats for name, breaker in cls._breakers.items()}
    
    @classmethod
    def reset_all(cls) -> None:
        """Reset all circuit breakers."""
        for breaker in cls._breakers.values():
            breaker.reset()


# Decorator for circuit-protected functions
def circuit_protected(service_name: str):
    """Decorator to wrap async function with circuit breaker.
    
    Usage:
        @circuit_protected("payment-api")
        async def call_payment_api(amount: float) -> Result[Payment, AppError]:
            ...
    """
    def decorator(fn: Callable[..., Awaitable[Result[T, AppError]]]):
        async def wrapper(*args, **kwargs) -> Result[T, AppError]:
            breaker = CircuitBreakerRegistry.get_sync(service_name)
            return await breaker.call(lambda: fn(*args, **kwargs))
        return wrapper
    return decorator

