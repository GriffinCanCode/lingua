"""Batch Operation Error Aggregation

Implements strategies for handling errors in batch operations:
- Fail-fast: Stop on first error
- Collect-all: Gather all errors before failing
- Partial success: Return successes with collected errors
"""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Awaitable, Callable, Generic, TypeVar

from core.errors import (
    AppError,
    ErrorCode,
    ErrorContext,
    Err,
    Ok,
    Result,
)

T = TypeVar("T")
U = TypeVar("U")


class BatchStrategy(Enum):
    """Available batch processing strategies."""
    FAIL_FAST = auto()      # Stop on first error
    COLLECT_ALL = auto()    # Collect all errors, then fail
    PARTIAL_SUCCESS = auto() # Return successes with errors


@dataclass(frozen=True)
class BatchItemResult(Generic[T]):
    """Result for a single item in a batch."""
    index: int
    input_key: str | None
    result: Result[T, AppError]
    duration_ms: float


@dataclass
class AggregatedError:
    """Aggregated error from multiple batch failures."""
    errors: list[BatchItemResult]
    message: str
    context: ErrorContext = field(default_factory=ErrorContext)
    
    @property
    def count(self) -> int:
        return len(self.errors)
    
    @property
    def error_codes(self) -> set[ErrorCode]:
        return {
            r.result.unwrap_err().code 
            for r in self.errors 
            if r.result.is_err()
        }
    
    def to_app_error(self) -> AppError:
        """Convert to single AppError for API response."""
        return AppError(
            code=ErrorCode.E5000_BUSINESS_GENERIC,
            message=self.message,
            context=self.context,
            metadata={
                "error_count": self.count,
                "failed_indices": [r.index for r in self.errors],
                "error_codes": [r.result.unwrap_err().code.name for r in self.errors if r.result.is_err()],
            },
        )


@dataclass
class BatchResult(Generic[T]):
    """Result of a batch operation with full item results."""
    successes: list[BatchItemResult[T]]
    failures: list[BatchItemResult[T]]
    total_duration_ms: float
    strategy: BatchStrategy
    
    @property
    def success_count(self) -> int:
        return len(self.successes)
    
    @property
    def failure_count(self) -> int:
        return len(self.failures)
    
    @property
    def total_count(self) -> int:
        return self.success_count + self.failure_count
    
    @property
    def success_rate(self) -> float:
        if self.total_count == 0:
            return 1.0
        return self.success_count / self.total_count
    
    @property
    def has_failures(self) -> bool:
        return self.failure_count > 0
    
    @property
    def all_succeeded(self) -> bool:
        return self.failure_count == 0
    
    def to_result(self) -> Result[list[T], AggregatedError]:
        """Convert to Result type.
        
        Returns Ok with all values if all succeeded.
        Returns Err with aggregated error if any failed.
        """
        if self.all_succeeded:
            return Ok([r.result.unwrap() for r in self.successes])
        
        return Err(AggregatedError(
            errors=self.failures,
            message=f"Batch operation failed: {self.failure_count}/{self.total_count} items failed",
        ))
    
    def values(self) -> list[T]:
        """Get all successful values."""
        return [r.result.unwrap() for r in self.successes]


class BatchProcessor(Generic[T, U]):
    """Process items in batch with configurable error handling.
    
    Usage:
        processor = BatchProcessor(BatchStrategy.COLLECT_ALL)
        
        async def process_item(item: str) -> Result[int, AppError]:
            return Ok(len(item))
        
        result = await processor.execute(["a", "bb", "ccc"], process_item)
        print(f"Processed {result.success_count}/{result.total_count}")
    """
    
    def __init__(
        self,
        strategy: BatchStrategy = BatchStrategy.COLLECT_ALL,
        max_concurrent: int | None = None,
        continue_on_error: bool = True,
    ):
        self.strategy = strategy
        self.max_concurrent = max_concurrent
        self.continue_on_error = continue_on_error

    async def execute(
        self,
        items: list[T],
        processor: Callable[[T], Awaitable[Result[U, AppError]]],
        key_fn: Callable[[T], str] | None = None,
    ) -> BatchResult[U]:
        """Execute processor on all items.
        
        Args:
            items: Items to process
            processor: Async function to process each item
            key_fn: Optional function to extract key from item for error reporting
        """
        start = datetime.now(timezone.utc)
        
        if self.strategy == BatchStrategy.FAIL_FAST:
            return await self._execute_fail_fast(items, processor, key_fn, start)
        elif self.strategy == BatchStrategy.COLLECT_ALL:
            return await self._execute_collect_all(items, processor, key_fn, start)
        else:  # PARTIAL_SUCCESS
            return await self._execute_partial_success(items, processor, key_fn, start)

    async def _execute_fail_fast(
        self,
        items: list[T],
        processor: Callable[[T], Awaitable[Result[U, AppError]]],
        key_fn: Callable[[T], str] | None,
        start: datetime,
    ) -> BatchResult[U]:
        """Stop on first error."""
        successes: list[BatchItemResult[U]] = []
        failures: list[BatchItemResult[U]] = []
        
        for idx, item in enumerate(items):
            item_start = datetime.now(timezone.utc)
            key = key_fn(item) if key_fn else None
            
            try:
                result = await processor(item)
            except Exception as e:
                result = Err(AppError(
                    code=ErrorCode.E9001_UNEXPECTED_ERROR,
                    message=str(e),
                ).chain(e))
            
            duration = (datetime.now(timezone.utc) - item_start).total_seconds() * 1000
            item_result = BatchItemResult(
                index=idx,
                input_key=key,
                result=result,
                duration_ms=duration,
            )
            
            if result.is_err():
                failures.append(item_result)
                break  # Fail fast
            else:
                successes.append(item_result)
        
        end = datetime.now(timezone.utc)
        return BatchResult(
            successes=successes,
            failures=failures,
            total_duration_ms=(end - start).total_seconds() * 1000,
            strategy=self.strategy,
        )

    async def _execute_collect_all(
        self,
        items: list[T],
        processor: Callable[[T], Awaitable[Result[U, AppError]]],
        key_fn: Callable[[T], str] | None,
        start: datetime,
    ) -> BatchResult[U]:
        """Collect all results, including errors."""
        if self.max_concurrent:
            return await self._execute_with_semaphore(
                items, processor, key_fn, start
            )
        
        # Process all items concurrently
        async def process_with_timing(idx: int, item: T) -> BatchItemResult[U]:
            item_start = datetime.now(timezone.utc)
            key = key_fn(item) if key_fn else None
            
            try:
                result = await processor(item)
            except Exception as e:
                result = Err(AppError(
                    code=ErrorCode.E9001_UNEXPECTED_ERROR,
                    message=str(e),
                ).chain(e))
            
            duration = (datetime.now(timezone.utc) - item_start).total_seconds() * 1000
            return BatchItemResult(
                index=idx,
                input_key=key,
                result=result,
                duration_ms=duration,
            )
        
        tasks = [process_with_timing(idx, item) for idx, item in enumerate(items)]
        results = await asyncio.gather(*tasks)
        
        successes = [r for r in results if r.result.is_ok()]
        failures = [r for r in results if r.result.is_err()]
        
        end = datetime.now(timezone.utc)
        return BatchResult(
            successes=successes,
            failures=failures,
            total_duration_ms=(end - start).total_seconds() * 1000,
            strategy=self.strategy,
        )

    async def _execute_with_semaphore(
        self,
        items: list[T],
        processor: Callable[[T], Awaitable[Result[U, AppError]]],
        key_fn: Callable[[T], str] | None,
        start: datetime,
    ) -> BatchResult[U]:
        """Execute with concurrency limit."""
        semaphore = asyncio.Semaphore(self.max_concurrent or 10)
        
        async def process_with_semaphore(idx: int, item: T) -> BatchItemResult[U]:
            async with semaphore:
                item_start = datetime.now(timezone.utc)
                key = key_fn(item) if key_fn else None
                
                try:
                    result = await processor(item)
                except Exception as e:
                    result = Err(AppError(
                        code=ErrorCode.E9001_UNEXPECTED_ERROR,
                        message=str(e),
                    ).chain(e))
                
                duration = (datetime.now(timezone.utc) - item_start).total_seconds() * 1000
                return BatchItemResult(
                    index=idx,
                    input_key=key,
                    result=result,
                    duration_ms=duration,
                )
        
        tasks = [process_with_semaphore(idx, item) for idx, item in enumerate(items)]
        results = await asyncio.gather(*tasks)
        
        successes = [r for r in results if r.result.is_ok()]
        failures = [r for r in results if r.result.is_err()]
        
        end = datetime.now(timezone.utc)
        return BatchResult(
            successes=successes,
            failures=failures,
            total_duration_ms=(end - start).total_seconds() * 1000,
            strategy=self.strategy,
        )

    async def _execute_partial_success(
        self,
        items: list[T],
        processor: Callable[[T], Awaitable[Result[U, AppError]]],
        key_fn: Callable[[T], str] | None,
        start: datetime,
    ) -> BatchResult[U]:
        """Same as collect_all but treats partial success as acceptable."""
        return await self._execute_collect_all(items, processor, key_fn, start)


class TransactionBatch(Generic[T, U]):
    """Batch processor with transactional semantics.
    
    Either all items succeed or all changes are rolled back.
    """
    
    def __init__(
        self,
        on_rollback: Callable[[list[U]], Awaitable[None]] | None = None,
    ):
        self.on_rollback = on_rollback
        self._committed: list[U] = []

    async def execute(
        self,
        items: list[T],
        processor: Callable[[T], Awaitable[Result[U, AppError]]],
    ) -> Result[list[U], AggregatedError]:
        """Execute all items transactionally.
        
        On any failure, rolls back all previously committed items.
        """
        results: list[BatchItemResult[U]] = []
        self._committed = []
        
        for idx, item in enumerate(items):
            item_start = datetime.now(timezone.utc)
            
            try:
                result = await processor(item)
            except Exception as e:
                result = Err(AppError(
                    code=ErrorCode.E9001_UNEXPECTED_ERROR,
                    message=str(e),
                ).chain(e))
            
            duration = (datetime.now(timezone.utc) - item_start).total_seconds() * 1000
            item_result = BatchItemResult(
                index=idx,
                input_key=None,
                result=result,
                duration_ms=duration,
            )
            results.append(item_result)
            
            if result.is_err():
                # Rollback committed items
                if self.on_rollback and self._committed:
                    await self.on_rollback(self._committed)
                
                return Err(AggregatedError(
                    errors=[item_result],
                    message=f"Transaction failed at item {idx}: {result.unwrap_err().message}",
                ))
            
            self._committed.append(result.unwrap())
        
        return Ok(self._committed)


# Helper functions

async def batch_map(
    items: list[T],
    fn: Callable[[T], Awaitable[Result[U, AppError]]],
    strategy: BatchStrategy = BatchStrategy.COLLECT_ALL,
    max_concurrent: int | None = None,
) -> BatchResult[U]:
    """Convenience function for batch processing.
    
    Usage:
        async def process(item: str) -> Result[int, AppError]:
            return Ok(len(item))
        
        result = await batch_map(["a", "bb"], process)
    """
    processor = BatchProcessor[T, U](strategy, max_concurrent)
    return await processor.execute(items, fn)


async def batch_map_fail_fast(
    items: list[T],
    fn: Callable[[T], Awaitable[Result[U, AppError]]],
) -> Result[list[U], AppError]:
    """Process items, stopping on first failure.
    
    Returns Ok with all values if all succeed.
    Returns first error encountered.
    """
    result = await batch_map(items, fn, BatchStrategy.FAIL_FAST)
    if result.has_failures:
        return Err(result.failures[0].result.unwrap_err())
    return Ok(result.values())


async def batch_map_collect_errors(
    items: list[T],
    fn: Callable[[T], Awaitable[Result[U, AppError]]],
) -> Result[list[U], list[AppError]]:
    """Process all items and collect all errors.
    
    Returns Ok with all values if all succeed.
    Returns all errors if any fail.
    """
    result = await batch_map(items, fn, BatchStrategy.COLLECT_ALL)
    if result.has_failures:
        return Err([r.result.unwrap_err() for r in result.failures])
    return Ok(result.values())

