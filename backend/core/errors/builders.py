"""Domain-Specific Error Builders

Ergonomic constructors for typed errors across all domains.
Each builder creates AppError with appropriate code and context.
"""
from dataclasses import dataclass
from typing import TypeVar
from uuid import UUID

from .types import AppError, ErrorCode, ErrorContext, Err, Result

T = TypeVar("T")


# =============================================================================
# Network Errors (E1xxx)
# =============================================================================

def network_error(
    message: str,
    *,
    code: ErrorCode = ErrorCode.E1000_NETWORK_GENERIC,
    url: str | None = None,
    status_code: int | None = None,
    origin: str = "",
    cause: Exception | None = None,
    **metadata,
) -> Err[AppError]:
    """Create network/external service error."""
    meta = {"url": url, "status_code": status_code, **metadata}
    return Err(AppError(
        code=code,
        message=message,
        context=ErrorContext(origin=origin),
        metadata={k: v for k, v in meta.items() if v is not None},
        cause=cause,
    ))


def connection_refused(host: str, port: int, origin: str = "") -> Err[AppError]:
    return network_error(
        f"Connection refused to {host}:{port}",
        code=ErrorCode.E1001_CONNECTION_REFUSED,
        origin=origin,
        host=host,
        port=port,
    )


def timeout_error(
    operation: str, timeout_seconds: float, origin: str = ""
) -> Err[AppError]:
    return network_error(
        f"Operation '{operation}' timed out after {timeout_seconds}s",
        code=ErrorCode.E1002_TIMEOUT,
        origin=origin,
        operation=operation,
        timeout_seconds=timeout_seconds,
    )


def external_service_unavailable(
    service: str, reason: str = "", origin: str = ""
) -> Err[AppError]:
    msg = f"External service '{service}' unavailable"
    if reason:
        msg += f": {reason}"
    return network_error(
        msg,
        code=ErrorCode.E1010_EXTERNAL_SERVICE_UNAVAILABLE,
        origin=origin,
        service=service,
    )


def circuit_open(service: str, origin: str = "") -> Err[AppError]:
    return network_error(
        f"Circuit breaker open for service '{service}'",
        code=ErrorCode.E1012_CIRCUIT_OPEN,
        origin=origin,
        service=service,
    )


def rate_limited(
    service: str, retry_after: float | None = None, origin: str = ""
) -> Err[AppError]:
    return network_error(
        f"Rate limited by '{service}'",
        code=ErrorCode.E1013_RATE_LIMITED,
        origin=origin,
        service=service,
        retry_after=retry_after,
    )


# =============================================================================
# Validation Errors (E2xxx)
# =============================================================================

def validation_error(
    message: str,
    *,
    code: ErrorCode = ErrorCode.E2000_VALIDATION_GENERIC,
    field: str | None = None,
    value: str | None = None,
    origin: str = "",
    **metadata,
) -> Err[AppError]:
    """Create validation error."""
    meta = {"field": field, "value": value, **metadata}
    return Err(AppError(
        code=code,
        message=message,
        context=ErrorContext(origin=origin),
        metadata={k: v for k, v in meta.items() if v is not None},
    ))


def required_field(field: str, origin: str = "") -> Err[AppError]:
    return validation_error(
        f"Required field '{field}' is missing",
        code=ErrorCode.E2001_REQUIRED_FIELD_MISSING,
        field=field,
        origin=origin,
    )


def invalid_format(
    field: str, expected: str, got: str | None = None, origin: str = ""
) -> Err[AppError]:
    msg = f"Invalid format for '{field}': expected {expected}"
    if got:
        msg += f", got '{got}'"
    return validation_error(
        msg,
        code=ErrorCode.E2002_INVALID_FORMAT,
        field=field,
        expected=expected,
        origin=origin,
    )


def out_of_range(
    field: str,
    value: int | float,
    min_val: int | float | None = None,
    max_val: int | float | None = None,
    origin: str = "",
) -> Err[AppError]:
    bounds = []
    if min_val is not None:
        bounds.append(f">= {min_val}")
    if max_val is not None:
        bounds.append(f"<= {max_val}")
    msg = f"Value {value} for '{field}' out of range ({', '.join(bounds)})"
    return validation_error(
        msg,
        code=ErrorCode.E2003_OUT_OF_RANGE,
        field=field,
        value=str(value),
        min=min_val,
        max=max_val,
        origin=origin,
    )


def invalid_email(email: str, origin: str = "") -> Err[AppError]:
    return validation_error(
        f"Invalid email address: '{email}'",
        code=ErrorCode.E2010_INVALID_EMAIL,
        field="email",
        value=email,
        origin=origin,
    )


def invalid_uuid(value: str, field: str = "id", origin: str = "") -> Err[AppError]:
    return validation_error(
        f"Invalid UUID format for '{field}': '{value}'",
        code=ErrorCode.E2011_INVALID_UUID,
        field=field,
        value=value,
        origin=origin,
    )


def invalid_json(message: str, origin: str = "") -> Err[AppError]:
    return validation_error(
        f"Invalid JSON: {message}",
        code=ErrorCode.E2021_INVALID_JSON,
        origin=origin,
    )


# =============================================================================
# Authentication/Authorization Errors (E3xxx)
# =============================================================================

def auth_error(
    message: str,
    *,
    code: ErrorCode = ErrorCode.E3000_AUTH_GENERIC,
    user_id: str | None = None,
    origin: str = "",
    **metadata,
) -> Err[AppError]:
    """Create authentication/authorization error."""
    ctx = ErrorContext(origin=origin, user_id=user_id)
    return Err(AppError(
        code=code,
        message=message,
        context=ctx,
        metadata=metadata,
    ))


def invalid_credentials(origin: str = "") -> Err[AppError]:
    return auth_error(
        "Invalid email or password",
        code=ErrorCode.E3001_INVALID_CREDENTIALS,
        origin=origin,
    )


def token_expired(origin: str = "") -> Err[AppError]:
    return auth_error(
        "Authentication token has expired",
        code=ErrorCode.E3002_TOKEN_EXPIRED,
        origin=origin,
    )


def token_invalid(reason: str = "", origin: str = "") -> Err[AppError]:
    msg = "Invalid authentication token"
    if reason:
        msg += f": {reason}"
    return auth_error(
        msg,
        code=ErrorCode.E3003_TOKEN_INVALID,
        origin=origin,
    )


def token_missing(origin: str = "") -> Err[AppError]:
    return auth_error(
        "Authentication token required",
        code=ErrorCode.E3004_TOKEN_MISSING,
        origin=origin,
    )


def insufficient_permissions(
    action: str, resource: str | None = None, user_id: str | None = None, origin: str = ""
) -> Err[AppError]:
    msg = f"Insufficient permissions to {action}"
    if resource:
        msg += f" on {resource}"
    return auth_error(
        msg,
        code=ErrorCode.E3010_INSUFFICIENT_PERMISSIONS,
        user_id=user_id,
        action=action,
        resource=resource,
        origin=origin,
    )


def resource_forbidden(
    resource: str, user_id: str | None = None, origin: str = ""
) -> Err[AppError]:
    return auth_error(
        f"Access to '{resource}' is forbidden",
        code=ErrorCode.E3011_RESOURCE_FORBIDDEN,
        user_id=user_id,
        resource=resource,
        origin=origin,
    )


def account_disabled(user_id: str | None = None, origin: str = "") -> Err[AppError]:
    return auth_error(
        "Account has been disabled",
        code=ErrorCode.E3020_ACCOUNT_DISABLED,
        user_id=user_id,
        origin=origin,
    )


# =============================================================================
# Database Errors (E4xxx)
# =============================================================================

def db_error(
    message: str,
    *,
    code: ErrorCode = ErrorCode.E4000_DATABASE_GENERIC,
    table: str | None = None,
    query: str | None = None,
    origin: str = "",
    cause: Exception | None = None,
    **metadata,
) -> Err[AppError]:
    """Create database error."""
    meta = {"table": table, **metadata}
    if query:
        meta["query"] = query[:200]  # Truncate for safety
    return Err(AppError(
        code=code,
        message=message,
        context=ErrorContext(origin=origin),
        metadata={k: v for k, v in meta.items() if v is not None},
        cause=cause,
    ))


def not_found(
    entity: str,
    id: str | UUID | None = None,
    origin: str = "",
) -> Err[AppError]:
    msg = f"{entity} not found"
    if id:
        msg += f": {id}"
    return db_error(
        msg,
        code=ErrorCode.E4010_NOT_FOUND,
        entity=entity,
        entity_id=str(id) if id else None,
        origin=origin,
    )


def duplicate_key(
    entity: str, field: str, value: str, origin: str = ""
) -> Err[AppError]:
    return db_error(
        f"{entity} with {field}='{value}' already exists",
        code=ErrorCode.E4011_DUPLICATE_KEY,
        entity=entity,
        field=field,
        value=value,
        origin=origin,
    )


def foreign_key_violation(
    entity: str, reference: str, origin: str = ""
) -> Err[AppError]:
    return db_error(
        f"Referenced {reference} does not exist for {entity}",
        code=ErrorCode.E4012_FOREIGN_KEY_VIOLATION,
        entity=entity,
        reference=reference,
        origin=origin,
    )


def db_connection_failed(reason: str = "", origin: str = "") -> Err[AppError]:
    msg = "Database connection failed"
    if reason:
        msg += f": {reason}"
    return db_error(
        msg,
        code=ErrorCode.E4001_CONNECTION_FAILED,
        origin=origin,
    )


def transaction_failed(reason: str = "", origin: str = "") -> Err[AppError]:
    msg = "Database transaction failed"
    if reason:
        msg += f": {reason}"
    return db_error(
        msg,
        code=ErrorCode.E4003_TRANSACTION_FAILED,
        origin=origin,
    )


# =============================================================================
# Business Logic Errors (E5xxx)
# =============================================================================

def business_error(
    message: str,
    *,
    code: ErrorCode = ErrorCode.E5000_BUSINESS_GENERIC,
    origin: str = "",
    **metadata,
) -> Err[AppError]:
    """Create business logic error."""
    return Err(AppError(
        code=code,
        message=message,
        context=ErrorContext(origin=origin),
        metadata=metadata,
    ))


def operation_not_allowed(
    operation: str, reason: str = "", origin: str = ""
) -> Err[AppError]:
    msg = f"Operation '{operation}' not allowed"
    if reason:
        msg += f": {reason}"
    return business_error(
        msg,
        code=ErrorCode.E5001_OPERATION_NOT_ALLOWED,
        operation=operation,
        origin=origin,
    )


def state_conflict(
    entity: str, current_state: str, required_state: str, origin: str = ""
) -> Err[AppError]:
    return business_error(
        f"{entity} is in '{current_state}' state, requires '{required_state}'",
        code=ErrorCode.E5002_STATE_CONFLICT,
        entity=entity,
        current_state=current_state,
        required_state=required_state,
        origin=origin,
    )


def precondition_failed(
    condition: str, reason: str = "", origin: str = ""
) -> Err[AppError]:
    msg = f"Precondition failed: {condition}"
    if reason:
        msg += f" ({reason})"
    return business_error(
        msg,
        code=ErrorCode.E5003_PRECONDITION_FAILED,
        condition=condition,
        origin=origin,
    )


def quota_exceeded(
    resource: str, limit: int, current: int, origin: str = ""
) -> Err[AppError]:
    return business_error(
        f"Quota exceeded for '{resource}': {current}/{limit}",
        code=ErrorCode.E5010_QUOTA_EXCEEDED,
        resource=resource,
        limit=limit,
        current=current,
        origin=origin,
    )


def limit_reached(resource: str, limit: int, origin: str = "") -> Err[AppError]:
    return business_error(
        f"Limit of {limit} reached for '{resource}'",
        code=ErrorCode.E5011_LIMIT_REACHED,
        resource=resource,
        limit=limit,
        origin=origin,
    )


# =============================================================================
# Internal Errors (E9xxx)
# =============================================================================

def internal_error(
    message: str,
    *,
    code: ErrorCode = ErrorCode.E9001_UNEXPECTED_ERROR,
    origin: str = "",
    cause: Exception | None = None,
    **metadata,
) -> Err[AppError]:
    """Create internal/unexpected error."""
    return Err(AppError(
        code=code,
        message=message,
        context=ErrorContext(origin=origin),
        metadata=metadata,
        cause=cause,
    ))


def not_implemented(feature: str, origin: str = "") -> Err[AppError]:
    return internal_error(
        f"Feature '{feature}' is not implemented",
        code=ErrorCode.E9002_NOT_IMPLEMENTED,
        feature=feature,
        origin=origin,
    )


def assertion_failed(condition: str, origin: str = "") -> Err[AppError]:
    return internal_error(
        f"Assertion failed: {condition}",
        code=ErrorCode.E9003_ASSERTION_FAILED,
        condition=condition,
        origin=origin,
    )

