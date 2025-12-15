"""FastAPI Exception Handlers

Integrates the monadic error handling system with FastAPI's exception
handling. Converts AppErrors and standard exceptions to proper HTTP responses.
"""
from __future__ import annotations

from typing import Callable

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.logging import get_logger, bind_context

from .types import AppError, ErrorCode, ErrorContext
from .boundaries import ValidationErrorMapper

log = get_logger("errors.handlers")


class AppErrorException(Exception):
    """Exception wrapper for AppError.
    
    Use this when you need to raise an AppError in code that
    doesn't use the Result monad (e.g., FastAPI dependencies).
    """
    
    def __init__(self, error: AppError):
        self.error = error
        super().__init__(str(error))


def result_to_response(error: AppError) -> JSONResponse:
    """Convert AppError to FastAPI JSONResponse."""
    status_code = error.code.http_status
    
    # Log the error with full context
    log_method = log.warning if status_code < 500 else log.error
    log_method(
        "error_response",
        error_code=error.code.name,
        error_code_num=error.code.value,
        message=error.message,
        category=error.code.category,
        correlation_id=error.context.correlation_id,
        origin=error.context.origin,
        metadata=error.metadata,
    )
    
    return JSONResponse(
        status_code=status_code,
        content=error.to_dict(),
    )


async def app_error_handler(request: Request, exc: AppErrorException) -> JSONResponse:
    """Handle AppErrorException raised in route handlers."""
    # Inject request context
    error = exc.error.with_context(
        request_id=request.headers.get("X-Request-ID"),
        correlation_id=request.headers.get("X-Correlation-ID") or exc.error.context.correlation_id,
    )
    return result_to_response(error)


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle standard HTTP exceptions with structured error response."""
    # Map HTTP status to appropriate error code
    status_code = exc.status_code
    if status_code == 400:
        code = ErrorCode.E2000_VALIDATION_GENERIC
    elif status_code == 401:
        code = ErrorCode.E3004_TOKEN_MISSING
    elif status_code == 403:
        code = ErrorCode.E3011_RESOURCE_FORBIDDEN
    elif status_code == 404:
        code = ErrorCode.E4010_NOT_FOUND
    elif status_code == 409:
        code = ErrorCode.E5002_STATE_CONFLICT
    elif status_code == 422:
        code = ErrorCode.E2000_VALIDATION_GENERIC
    elif status_code == 429:
        code = ErrorCode.E1013_RATE_LIMITED
    elif status_code >= 500:
        code = ErrorCode.E9001_UNEXPECTED_ERROR
    else:
        code = ErrorCode.E9000_INTERNAL_GENERIC
    
    error = AppError(
        code=code,
        message=str(exc.detail) if exc.detail else f"HTTP {status_code}",
        context=ErrorContext(
            correlation_id=request.headers.get("X-Correlation-ID", ""),
            origin="http",
        ),
    )
    
    return result_to_response(error)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors with detailed field information."""
    mapper = ValidationErrorMapper("request_validation")
    errors = mapper.map_pydantic_errors(exc.errors())
    
    # Create aggregated error
    if len(errors) == 1:
        error = errors[0]
    else:
        error = AppError(
            code=ErrorCode.E2000_VALIDATION_GENERIC,
            message=f"Validation failed: {len(errors)} errors",
            context=ErrorContext(
                correlation_id=request.headers.get("X-Correlation-ID", ""),
                origin="request_validation",
            ),
            metadata={
                "errors": [
                    {
                        "code": e.code.name,
                        "message": e.message,
                        "field": e.metadata.get("field"),
                    }
                    for e in errors
                ],
            },
        )
    
    return result_to_response(error)


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Catch-all handler for unhandled exceptions.
    
    Converts to internal error and logs full traceback.
    """
    error = AppError(
        code=ErrorCode.E9001_UNEXPECTED_ERROR,
        message="An unexpected error occurred",
        context=ErrorContext(
            correlation_id=request.headers.get("X-Correlation-ID", ""),
            origin="unhandled",
        ),
        cause=exc,
    )
    
    # Log with traceback for debugging
    log.exception(
        "unhandled_exception",
        error_type=type(exc).__name__,
        error_message=str(exc),
        correlation_id=error.context.correlation_id,
    )
    
    return result_to_response(error)


def register_error_handlers(app: FastAPI) -> None:
    """Register all error handlers on FastAPI app.
    
    Usage in main.py:
        from core.errors.handlers import register_error_handlers
        
        app = FastAPI(...)
        register_error_handlers(app)
    """
    app.add_exception_handler(AppErrorException, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)


# Utility function to raise AppError in non-Result contexts
def raise_error(error: AppError) -> None:
    """Raise AppError as exception.
    
    Use when you need to exit early from code that doesn't
    use the Result monad.
    
    Usage:
        if not user:
            raise_error(not_found("User", user_id).error)
    """
    raise AppErrorException(error)


def raise_result(result) -> None:
    """Raise error if Result is Err, otherwise return.
    
    Useful for converting Result to exception-based flow.
    
    Usage:
        result = validate_input(data)
        raise_result(result)  # Raises if Err
        # Continue with Ok value...
    """
    if result.is_err():
        raise AppErrorException(result.unwrap_err())

