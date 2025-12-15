"""Resilience Patterns

Provides robust error handling and fault tolerance for external operations:
- Circuit breakers for external service protection
- Retry policies with configurable backoff
- Batch processing with error aggregation
"""
from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerRegistry,
    CircuitState,
    CircuitStats,
    circuit_protected,
)

from .retry import (
    BackoffStrategy,
    CombinedPolicy,
    RetryConfig,
    RetryPolicy,
    RetryResult,
    TimeoutPolicy,
    retryable,
    with_timeout,
)

from .batch import (
    AggregatedError,
    BatchItemResult,
    BatchProcessor,
    BatchResult,
    BatchStrategy,
    TransactionBatch,
    batch_map,
    batch_map_collect_errors,
    batch_map_fail_fast,
)

__all__ = [
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerRegistry",
    "CircuitState",
    "CircuitStats",
    "circuit_protected",
    # Retry
    "BackoffStrategy",
    "CombinedPolicy",
    "RetryConfig",
    "RetryPolicy",
    "RetryResult",
    "TimeoutPolicy",
    "retryable",
    "with_timeout",
    # Batch
    "AggregatedError",
    "BatchItemResult",
    "BatchProcessor",
    "BatchResult",
    "BatchStrategy",
    "TransactionBatch",
    "batch_map",
    "batch_map_collect_errors",
    "batch_map_fail_fast",
]

