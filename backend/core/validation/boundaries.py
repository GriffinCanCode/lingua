"""Validation at System Boundaries

Parse-don't-validate semantics at system boundaries:
- API ingress: Validate and parse incoming requests
- Database egress: Validate and parse database results
- External service calls: Validate external API responses

Invalid data becomes unrepresentable once parsed through boundaries.
"""
from __future__ import annotations

from typing import Any, Callable, TypeVar, Generic, overload
from functools import wraps
from dataclasses import dataclass

from fastapi import Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import AppError, ErrorCode, Result, Ok, Err
from .schema import BaseSchema, ValidationMode
from .errors import ValidationError, ValidationErrorDetail, create_accumulator

T = TypeVar("T")
S = TypeVar("S", bound=BaseSchema)


# ============================================================================
# Boundary Validators
# ============================================================================

class BoundaryValidator(Generic[S]):
    """Stateless boundary validator for a specific schema.
    
    Usage:
        user_validator = BoundaryValidator(UserSchema)
        result = user_validator.parse_ingress(request_data)
    """
    
    __slots__ = ("schema", "mode", "sensitive_fields")
    
    def __init__(self, schema: type[S], mode: ValidationMode = ValidationMode.FAIL_FAST):
        self.schema, self.mode = schema, mode
        self.sensitive_fields = getattr(schema, "_sensitive_fields", frozenset())
    
    def parse_ingress(self, data: dict[str, Any], *, strict: bool = True) -> Result[S, AppError]:
        """Parse and validate data entering the system. Use for: API request bodies, form submissions, file uploads."""
        try: return Ok(self.schema.parse(data, strict=strict))
        except ValidationError as e: return Err(e.to_app_error().with_context(origin="ingress"))
        except Exception as e:
            return Err(AppError(code=ErrorCode.E2000_VALIDATION_GENERIC, message=f"Ingress validation failed: {e}",
                metadata={"schema": self.schema.__name__}))
    
    def parse_egress(self, data: Any) -> Result[S, AppError]:
        """Parse and validate data leaving to external consumers. Use for: API response serialization, export data."""
        try:
            return Ok(self.schema.parse(data, strict=False) if isinstance(data, dict) else self.schema.model_validate(data))
        except ValidationError as e: return Err(e.to_app_error().with_context(origin="egress"))
        except Exception as e:
            return Err(AppError(code=ErrorCode.E2000_VALIDATION_GENERIC, message=f"Egress validation failed: {e}",
                metadata={"schema": self.schema.__name__}))
    
    def parse_db(self, data: Any) -> Result[S, AppError]:
        """Parse and validate data from database.
        
        Use for: Database query results, ORM model serialization.
        """
        try:
            if isinstance(data, dict):
                validated = self.schema.parse(data, strict=False)
            elif hasattr(data, "__dict__"):
                # SQLAlchemy model
                validated = self.schema.model_validate(data)
            else:
                validated = self.schema.model_validate(data)
            return Ok(validated)
        except ValidationError as e:
            return Err(e.to_app_error().with_context(origin="database_egress"))
        except Exception as e:
            return Err(AppError(
                code=ErrorCode.E4002_QUERY_FAILED,
                message=f"Database egress validation failed: {e}",
                metadata={"schema": self.schema.__name__},
            ))
    
    def parse_external(self, data: dict[str, Any], service_name: str = "external") -> Result[S, AppError]:
        """Parse and validate external service response.
        
        Use for: Third-party API responses, webhook payloads.
        """
        try:
            validated = self.schema.parse(data, strict=False)
            return Ok(validated)
        except ValidationError as e:
            return Err(AppError(
                code=ErrorCode.E1011_EXTERNAL_SERVICE_ERROR,
                message=f"{service_name} returned invalid response",
                metadata={
                    "service": service_name,
                    "validation_errors": e.to_dict(redact_sensitive=True),
                },
            ))
        except Exception as e:
            return Err(AppError(
                code=ErrorCode.E1011_EXTERNAL_SERVICE_ERROR,
                message=f"{service_name} response parsing failed: {e}",
            ))


# ============================================================================
# Decorator-based Boundary Validation
# ============================================================================

def validate_request(
    schema: type[S],
    *,
    mode: ValidationMode = ValidationMode.FAIL_FAST,
    strict: bool = True,
) -> Callable:
    """Decorator to validate API request body at ingress.
    
    Usage:
        @router.post("/users")
        @validate_request(UserCreate)
        async def create_user(data: UserCreate):
            ...
    """
    validator = BoundaryValidator(schema, mode)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find request body in kwargs (FastAPI injects it)
            for key, value in list(kwargs.items()):
                if isinstance(value, schema):
                    # Already validated by FastAPI/Pydantic
                    return await func(*args, **kwargs)
                if isinstance(value, dict):
                    # Validate dict against schema
                    result = validator.parse_ingress(value, strict=strict)
                    if result.is_err():
                        from core.errors import raise_error
                        raise_error(result.unwrap_err())
                    kwargs[key] = result.unwrap()
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def validate_response(
    schema: type[S],
    *,
    mode: ValidationMode = ValidationMode.FAIL_FAST,
) -> Callable:
    """Decorator to validate API response at egress.
    
    Usage:
        @router.get("/users/{id}")
        @validate_response(UserResponse)
        async def get_user(id: UUID):
            return db.get_user(id)
    """
    validator = BoundaryValidator(schema, mode)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            # Validate response
            parse_result = validator.parse_egress(result)
            if parse_result.is_err():
                # Log error but return original (don't expose internal error)
                from core.logging import get_logger
                log = get_logger("validation.boundaries")
                log.error(
                    "response_validation_failed",
                    error=parse_result.unwrap_err().message,
                    schema=schema.__name__,
                )
                # Return original result (fail open for responses)
                return result
            
            return parse_result.unwrap()
        return wrapper
    return decorator


def validate_external(
    schema: type[S],
    service_name: str,
    *,
    mode: ValidationMode = ValidationMode.FAIL_FAST,
) -> Callable[[Callable], Callable]:
    """Decorator to validate external service response.
    
    Usage:
        @validate_external(WeatherResponse, "weather_api")
        async def fetch_weather(city: str) -> WeatherResponse:
            response = await http.get(f"/weather/{city}")
            return response.json()
    """
    validator = BoundaryValidator(schema, mode)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            if isinstance(result, dict):
                parse_result = validator.parse_external(result, service_name)
                if parse_result.is_err():
                    from core.errors import raise_error
                    raise_error(parse_result.unwrap_err())
                return parse_result.unwrap()
            
            return result
        return wrapper
    return decorator


# ============================================================================
# Functional Boundary Parsers
# ============================================================================

def parse_ingress(
    schema: type[S],
    data: dict[str, Any],
    *,
    strict: bool = True,
    mode: ValidationMode = ValidationMode.FAIL_FAST,
) -> Result[S, AppError]:
    """Parse and validate incoming data.
    
    Usage:
        result = parse_ingress(UserCreate, request.json())
        if result.is_err():
            return error_response(result.unwrap_err())
        user = result.unwrap()
    """
    return BoundaryValidator(schema, mode).parse_ingress(data, strict=strict)


def parse_db_egress(
    schema: type[S],
    data: Any,
    *,
    mode: ValidationMode = ValidationMode.FAIL_FAST,
) -> Result[S, AppError]:
    """Parse and validate database query result.
    
    Usage:
        row = await db.fetchone(query)
        result = parse_db_egress(UserResponse, row)
    """
    return BoundaryValidator(schema, mode).parse_db(data)


def parse_external(
    schema: type[S],
    data: dict[str, Any],
    service_name: str = "external",
    *,
    mode: ValidationMode = ValidationMode.FAIL_FAST,
) -> Result[S, AppError]:
    """Parse and validate external service response.
    
    Usage:
        response = await http_client.get(url)
        result = parse_external(WeatherResponse, response.json(), "weather_api")
    """
    return BoundaryValidator(schema, mode).parse_external(data, service_name)


# ============================================================================
# Batch Validation
# ============================================================================

def parse_batch(
    schema: type[S],
    items: list[dict[str, Any]],
    *,
    strict: bool = True,
    mode: ValidationMode = ValidationMode.COLLECT_ALL,
    max_errors: int = 50,
) -> Result[list[S], list[tuple[int, AppError]]]:
    """Parse and validate a batch of items.
    
    Returns Ok with all valid items or Err with (index, error) pairs.
    
    Usage:
        result = parse_batch(UserCreate, users_data)
        match result:
            case Ok(users):
                await db.bulk_insert(users)
            case Err(errors):
                for idx, err in errors:
                    log.error(f"Item {idx}: {err.message}")
    """
    validator = BoundaryValidator(schema, mode)
    valid: list[S] = []
    errors: list[tuple[int, AppError]] = []
    
    for idx, item in enumerate(items):
        if len(errors) >= max_errors:
            break
        
        result = validator.parse_ingress(item, strict=strict)
        if result.is_ok():
            valid.append(result.unwrap())
        else:
            error = result.unwrap_err().with_metadata(batch_index=idx)
            errors.append((idx, error))
    
    if errors:
        return Err(errors)
    return Ok(valid)


# ============================================================================
# FastAPI Integration
# ============================================================================

class ValidatedBody(Generic[S]):
    """FastAPI dependency for validated request body.
    
    Usage:
        @router.post("/users")
        async def create_user(body: Annotated[UserCreate, ValidatedBody(UserCreate)]):
            ...
    """
    
    def __init__(
        self,
        schema: type[S],
        *,
        mode: ValidationMode = ValidationMode.FAIL_FAST,
        strict: bool = True,
    ):
        self.schema = schema
        self.mode = mode
        self.strict = strict
        self.validator = BoundaryValidator(schema, mode)
    
    async def __call__(self, request: Request) -> S:
        try:
            body = await request.json()
        except Exception as e:
            from core.errors import raise_error
            raise_error(AppError(
                code=ErrorCode.E2021_INVALID_JSON,
                message=f"Invalid JSON in request body: {e}",
            ))
        
        result = self.validator.parse_ingress(body, strict=self.strict)
        if result.is_err():
            from core.errors import raise_error
            raise_error(result.unwrap_err())
        
        return result.unwrap()


def validated_body(
    schema: type[S],
    *,
    mode: ValidationMode = ValidationMode.FAIL_FAST,
    strict: bool = True,
) -> Callable:
    """FastAPI dependency factory for validated request body.
    
    Usage:
        @router.post("/users")
        async def create_user(body: UserCreate = Depends(validated_body(UserCreate))):
            ...
    """
    validator = ValidatedBody(schema, mode=mode, strict=strict)
    return Depends(validator)


# ============================================================================
# Context Manager for Multiple Validations
# ============================================================================

class ValidationBoundary:
    """Context manager for validating multiple fields with accumulation.
    
    Usage:
        async with ValidationBoundary(mode=ValidationMode.COLLECT_ALL) as boundary:
            user = boundary.parse("user", user_data, UserSchema)
            address = boundary.parse("address", addr_data, AddressSchema)
        # Raises ValidationError if any parsing failed
    """
    
    def __init__(
        self,
        mode: ValidationMode = ValidationMode.FAIL_FAST,
        max_errors: int = 50,
        sensitive_fields: frozenset[str] | None = None,
    ):
        self.mode = mode
        self.max_errors = max_errors
        self.sensitive_fields = sensitive_fields
        self._accumulator = create_accumulator(mode, max_errors)
        self._results: dict[str, Any] = {}
    
    async def __aenter__(self) -> ValidationBoundary:
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is None:
            self._accumulator.raise_if_errors(sensitive_fields=self.sensitive_fields)
        return False
    
    def __enter__(self) -> ValidationBoundary:
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is None:
            self._accumulator.raise_if_errors(sensitive_fields=self.sensitive_fields)
        return False
    
    def parse(
        self,
        name: str,
        data: dict[str, Any] | Any,
        schema: type[S],
        *,
        strict: bool = True,
    ) -> S | None:
        """Parse data against schema, accumulating errors.
        
        Returns the parsed schema or None if validation failed.
        """
        try:
            if isinstance(data, dict):
                validated = schema.parse(data, strict=strict)
            else:
                validated = schema.model_validate(data)
            self._results[name] = validated
            return validated
        except ValidationError as e:
            for detail in e.details:
                prefixed_detail = ValidationErrorDetail(
                    field_path=f"{name}.{detail.field_path}" if detail.field_path != "$" else name,
                    constraint=detail.constraint,
                    actual_value=detail.actual_value,
                    message=detail.message,
                    suggested_fix=detail.suggested_fix,
                )
                should_continue = self._accumulator.add_error(prefixed_detail)
                if not should_continue:
                    break
            return None
        except Exception as e:
            detail = ValidationErrorDetail(
                field_path=name,
                constraint="parse_error",
                message=str(e),
            )
            self._accumulator.add_error(detail)
            return None
    
    def get(self, name: str) -> Any:
        """Get a previously parsed result."""
        return self._results.get(name)
    
    @property
    def has_errors(self) -> bool:
        """Check if any errors accumulated."""
        return self._accumulator.has_errors()
    
    @property
    def errors(self) -> list[ValidationErrorDetail]:
        """Get accumulated errors."""
        return self._accumulator.get_errors()
