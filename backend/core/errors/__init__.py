"""Monadic Error Handling System

This module provides a comprehensive, type-safe error handling system inspired
by Haskell's Either monad and Rust's Result type.

Key components:
- Result[T, E]: Monadic container for success/failure
- AppError: Base error type with full context
- ErrorCode: Hierarchical error code taxonomy
- Builder functions: Ergonomic error construction

Usage:
    from core.errors import Ok, Err, Result, AppError, not_found

    def find_user(user_id: str) -> Result[User, AppError]:
        user = db.get(user_id)
        if not user:
            return not_found("User", user_id, origin="user_service")
        return Ok(user)

    # Pattern matching (exhaustive)
    match find_user("123"):
        case Ok(user):
            print(f"Found: {user.name}")
        case Err(error):
            log.error(error.message, code=error.code.name)
"""
from .types import (
    # Core types
    Result,
    Ok,
    Err,
    AppError,
    ErrorCode,
    ErrorContext,
    # Constructors
    ok,
    err,
    from_exception,
    try_result,
    try_result_async,
    # Combinators
    collect_results,
    sequence_results,
    ensure,
    require,
)

from .builders import (
    # Network (E1xxx)
    network_error,
    connection_refused,
    timeout_error,
    external_service_unavailable,
    circuit_open,
    rate_limited,
    # Validation (E2xxx)
    validation_error,
    required_field,
    invalid_format,
    out_of_range,
    invalid_email,
    invalid_uuid,
    invalid_json,
    # Auth (E3xxx)
    auth_error,
    invalid_credentials,
    token_expired,
    token_invalid,
    token_missing,
    insufficient_permissions,
    resource_forbidden,
    account_disabled,
    # Database (E4xxx)
    db_error,
    not_found,
    duplicate_key,
    foreign_key_violation,
    db_connection_failed,
    transaction_failed,
    # Business (E5xxx)
    business_error,
    operation_not_allowed,
    state_conflict,
    precondition_failed,
    quota_exceeded,
    limit_reached,
    # Internal (E9xxx)
    internal_error,
    not_implemented,
    assertion_failed,
)

from .boundaries import (
    # Mappers
    ErrorMapper,
    DatabaseErrorMapper,
    AuthErrorMapper,
    ValidationErrorMapper,
    EngineErrorMapper,
    # Decorators
    map_errors,
    map_db_errors,
    map_auth_errors,
)

from .handlers import (
    AppErrorException,
    register_error_handlers,
    result_to_response,
    raise_error,
    raise_result,
)

__all__ = [
    # Core types
    "Result",
    "Ok",
    "Err",
    "AppError",
    "ErrorCode",
    "ErrorContext",
    # Constructors
    "ok",
    "err",
    "from_exception",
    "try_result",
    "try_result_async",
    # Combinators
    "collect_results",
    "sequence_results",
    "ensure",
    "require",
    # Network (E1xxx)
    "network_error",
    "connection_refused",
    "timeout_error",
    "external_service_unavailable",
    "circuit_open",
    "rate_limited",
    # Validation (E2xxx)
    "validation_error",
    "required_field",
    "invalid_format",
    "out_of_range",
    "invalid_email",
    "invalid_uuid",
    "invalid_json",
    # Auth (E3xxx)
    "auth_error",
    "invalid_credentials",
    "token_expired",
    "token_invalid",
    "token_missing",
    "insufficient_permissions",
    "resource_forbidden",
    "account_disabled",
    # Database (E4xxx)
    "db_error",
    "not_found",
    "duplicate_key",
    "foreign_key_violation",
    "db_connection_failed",
    "transaction_failed",
    # Business (E5xxx)
    "business_error",
    "operation_not_allowed",
    "state_conflict",
    "precondition_failed",
    "quota_exceeded",
    "limit_reached",
    # Internal (E9xxx)
    "internal_error",
    "not_implemented",
    "assertion_failed",
    # Boundary Mappers
    "ErrorMapper",
    "DatabaseErrorMapper",
    "AuthErrorMapper",
    "ValidationErrorMapper",
    "EngineErrorMapper",
    "map_errors",
    "map_db_errors",
    "map_auth_errors",
    # Handlers
    "AppErrorException",
    "register_error_handlers",
    "result_to_response",
    "raise_error",
    "raise_result",
]

