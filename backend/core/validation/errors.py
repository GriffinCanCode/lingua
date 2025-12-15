"""Validation Error System

Structured errors with JSON paths, constraints, actual values (redacted if sensitive),
and suggested fixes. Supports both fail-fast and collect-all accumulation modes.

Error Format:
{
    "error": {
        "type": "validation_error",
        "message": "Validation failed",
        "mode": "collect_all",
        "errors": [
            {
                "field": "user.email",
                "constraint": "email",
                "value": "invalid-email",
                "message": "Invalid email format",
                "suggested_fix": "Provide a valid email (e.g., 'user@example.com')"
            }
        ]
    }
}
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Sequence
from enum import Enum

from core.errors import AppError, ErrorCode
from .schema import ValidationMode


@dataclass(frozen=True, slots=True)
class ValidationErrorDetail:
    """Detailed validation error for a single field.
    
    Carries sufficient context for API consumers to programmatically remediate:
    - field_path: JSON path to offending field (e.g., "user.addresses[0].street")
    - constraint: Type of constraint violated (e.g., "email", "min_length[5]")
    - actual_value: The actual value that failed (may be redacted)
    - message: Human-readable error message
    - suggested_fix: Actionable suggestion to fix the error
    """
    field_path: str
    constraint: str
    actual_value: Any = None
    message: str = ""
    suggested_fix: str | None = None
    
    def redact_if_sensitive(self, sensitive_fields: frozenset[str] | set[str] | None = None) -> ValidationErrorDetail:
        """Redact actual value if field is sensitive."""
        if not sensitive_fields: return self
        path_parts = self.field_path.replace("[", ".").replace("]", "").split(".")
        if any(part in sensitive_fields for part in path_parts):
            return ValidationErrorDetail(field_path=self.field_path, constraint=self.constraint, actual_value="[REDACTED]",
                message=self.message, suggested_fix=self.suggested_fix)
        return self
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for API responses."""
        result = {"field": self.field_path, "constraint": self.constraint, "message": self.message}
        if self.actual_value is not None: result["value"] = self.actual_value
        if self.suggested_fix: result["suggested_fix"] = self.suggested_fix
        return result
    
    @classmethod
    def from_pydantic_error(cls, error: dict[str, Any], *, sensitive_fields: frozenset[str] | None = None) -> ValidationErrorDetail:
        """Create from Pydantic validation error dict."""
        loc = error.get("loc", ())
        actual = error.get("input")
        if sensitive_fields and {str(p) for p in loc} & sensitive_fields: actual = "[REDACTED]"
        return cls(field_path=cls._format_path(loc), constraint=error.get("type", "validation_error"),
            actual_value=actual, message=error.get("msg", "Validation failed"), suggested_fix=cls._generate_suggested_fix(error))
    
    @staticmethod
    def _format_path(loc: Sequence[str | int]) -> str:
        """Format Pydantic location tuple as JSON path."""
        if not loc: return "$"
        parts = []
        for segment in loc:
            if isinstance(segment, int): parts.append(f"[{segment}]")
            elif parts: parts.append(f".{segment}")
            else: parts.append(str(segment))
        return "".join(parts)
    
    @staticmethod
    def _generate_suggested_fix(error: dict[str, Any]) -> str | None:
        """Generate suggested fix from Pydantic error context."""
        err_type = error.get("type", "")
        ctx = error.get("ctx", {})
        
        fix_generators = {
            "string_too_short": lambda: f"Value must be at least {ctx.get('min_length', '?')} characters",
            "string_too_long": lambda: f"Truncate to {ctx.get('max_length', '?')} characters or less",
            "string_pattern_mismatch": lambda: f"Value must match pattern: {ctx.get('pattern', '?')}",
            "greater_than": lambda: f"Use a value greater than {ctx.get('gt', '?')}",
            "greater_than_equal": lambda: f"Use a value of {ctx.get('ge', '?')} or more",
            "less_than": lambda: f"Use a value less than {ctx.get('lt', '?')}",
            "less_than_equal": lambda: f"Use a value of {ctx.get('le', '?')} or less",
            "missing": lambda: "This field is required - provide a value",
            "extra_forbidden": lambda: "Remove this field - it is not allowed",
            "enum": lambda: f"Valid options: {', '.join(str(v) for v in ctx.get('expected', []))}",
            "uuid_parsing": lambda: "Provide a valid UUID (e.g., '550e8400-e29b-41d4-a716-446655440000')",
            "datetime_parsing": lambda: "Provide ISO8601 datetime (e.g., '2024-01-15T10:30:00Z')",
            "datetime_from_date_parsing": lambda: "Provide ISO8601 datetime (e.g., '2024-01-15T10:30:00Z')",
            "date_parsing": lambda: "Provide ISO8601 date (e.g., '2024-01-15')",
            "time_parsing": lambda: "Provide ISO8601 time (e.g., '10:30:00')",
            "int_parsing": lambda: "Provide a valid integer number",
            "int_from_float": lambda: "Provide an integer, not a decimal",
            "float_parsing": lambda: "Provide a valid decimal number",
            "bool_parsing": lambda: "Provide true or false",
            "url_parsing": lambda: "Provide a valid URL (e.g., 'https://example.com')",
            "url_scheme": lambda: f"URL must use scheme: {ctx.get('expected_schemes', 'http or https')}",
            "email": lambda: "Provide a valid email (e.g., 'user@example.com')",
            "json_invalid": lambda: "Provide valid JSON",
            "list_type": lambda: "Provide an array/list of values",
            "dict_type": lambda: "Provide an object with key-value pairs",
            "string_type": lambda: "Provide a string value",
            "int_type": lambda: "Provide an integer value",
            "float_type": lambda: "Provide a number value",
            "bool_type": lambda: "Provide a boolean (true/false) value",
            "none_required": lambda: "This field must be null",
            "value_error": lambda: ctx.get("message", "Invalid value"),
        }
        
        if err_type in fix_generators: return fix_generators[err_type]()
        return ctx.get("message")


@dataclass
class ValidationError(Exception):
    """Validation error with structured details.
    
    Carries sufficient context for API consumers to programmatically remediate.
    Supports both fail-fast and collect-all accumulation modes.
    """
    message: str
    details: list[ValidationErrorDetail]
    mode: ValidationMode = ValidationMode.FAIL_FAST
    sensitive_fields: frozenset[str] | None = None
    
    def __post_init__(self):
        super().__init__(self.message)
    
    def __str__(self) -> str:
        if not self.details: return self.message
        if len(self.details) == 1: return f"{(d := self.details[0]).field_path}: {d.message}"
        return f"{self.message} ({len(self.details)} errors)"
    
    @property
    def field_errors(self) -> dict[str, list[ValidationErrorDetail]]:
        """Group errors by field path."""
        result: dict[str, list[ValidationErrorDetail]] = {}
        for detail in self.details: result.setdefault(detail.field_path, []).append(detail)
        return result
    
    @property
    def first_error(self) -> ValidationErrorDetail | None: return self.details[0] if self.details else None
    
    def get_errors_for_field(self, field_path: str) -> list[ValidationErrorDetail]:
        return [d for d in self.details if d.field_path == field_path]
    
    def add_error(self, detail: ValidationErrorDetail) -> None: self.details.append(detail)
    
    def to_app_error(self) -> AppError:
        """Convert to AppError for error handling system."""
        redacted_details = ([d.redact_if_sensitive(self.sensitive_fields) for d in self.details]
            if self.sensitive_fields else self.details)
        
        if len(redacted_details) == 1:
            d = redacted_details[0]
            return AppError(code=ErrorCode.E2000_VALIDATION_GENERIC, message=f"{d.field_path}: {d.message}",
                metadata={"field": d.field_path, "constraint": d.constraint, "value": d.actual_value, "suggested_fix": d.suggested_fix})
        
        return AppError(code=ErrorCode.E2000_VALIDATION_GENERIC, message=f"Validation failed: {len(redacted_details)} errors",
            metadata={"validation_mode": self.mode.value, "error_count": len(redacted_details),
                "errors": [d.to_dict() for d in redacted_details]})
    
    def to_dict(self, *, redact_sensitive: bool = True) -> dict[str, Any]:
        """Serialize to dictionary for API responses."""
        details = ([d.redact_if_sensitive(self.sensitive_fields) for d in self.details]
            if redact_sensitive and self.sensitive_fields else self.details)
        return {"error": {"type": "validation_error", "message": self.message, "mode": self.mode.value,
            "error_count": len(details), "errors": [d.to_dict() for d in details]}}
    
    @classmethod
    def from_pydantic(cls, exc: Exception, *, mode: ValidationMode = ValidationMode.FAIL_FAST,
                      sensitive_fields: frozenset[str] | None = None) -> ValidationError:
        """Create from Pydantic ValidationError."""
        if not hasattr(exc, "errors"):
            return cls(message=str(exc), details=[], mode=mode, sensitive_fields=sensitive_fields)
        return cls(message="Validation failed",
            details=[ValidationErrorDetail.from_pydantic_error(err, sensitive_fields=sensitive_fields) for err in exc.errors()],
            mode=mode, sensitive_fields=sensitive_fields)


class ValidationErrorAccumulator(ABC):
    """Abstract base for error accumulation strategies."""
    
    @abstractmethod
    def add_error(self, detail: ValidationErrorDetail) -> bool:
        """Add error detail. Returns True if should continue, False if should stop."""
    
    @abstractmethod
    def get_errors(self) -> list[ValidationErrorDetail]:
        """Get accumulated errors."""
    
    @abstractmethod
    def has_errors(self) -> bool:
        """Check if any errors accumulated."""
    
    @abstractmethod
    def raise_if_errors(
        self,
        message: str = "Validation failed",
        sensitive_fields: frozenset[str] | None = None,
    ) -> None:
        """Raise ValidationError if errors exist."""
    
    @property
    @abstractmethod
    def mode(self) -> ValidationMode:
        """Get the accumulation mode."""
    
    def to_validation_error(self, message: str = "Validation failed", sensitive_fields: frozenset[str] | None = None) -> ValidationError | None:
        """Convert to ValidationError if errors exist."""
        if not self.has_errors(): return None
        return ValidationError(message=message, details=self.get_errors(), mode=self.mode, sensitive_fields=sensitive_fields)


@dataclass
class FailFastAccumulator(ValidationErrorAccumulator):
    """Fail-fast accumulator: stops on first error."""
    _error: ValidationErrorDetail | None = None
    
    @property
    def mode(self) -> ValidationMode: return ValidationMode.FAIL_FAST
    
    def add_error(self, detail: ValidationErrorDetail) -> bool:
        if self._error is None: self._error = detail
        return False
    
    def get_errors(self) -> list[ValidationErrorDetail]: return [self._error] if self._error else []
    
    def has_errors(self) -> bool: return self._error is not None
    
    def raise_if_errors(self, message: str = "Validation failed", sensitive_fields: frozenset[str] | None = None) -> None:
        if self._error:
            raise ValidationError(message=message, details=[self._error], mode=ValidationMode.FAIL_FAST, sensitive_fields=sensitive_fields)


@dataclass
class CollectAllAccumulator(ValidationErrorAccumulator):
    """Collect-all accumulator: gathers all errors up to max_errors."""
    _errors: list[ValidationErrorDetail] = field(default_factory=list)
    max_errors: int = 50
    
    @property
    def mode(self) -> ValidationMode: return ValidationMode.COLLECT_ALL
    
    def add_error(self, detail: ValidationErrorDetail) -> bool:
        if len(self._errors) < self.max_errors: self._errors.append(detail)
        return len(self._errors) < self.max_errors
    
    def get_errors(self) -> list[ValidationErrorDetail]: return self._errors.copy()
    
    def has_errors(self) -> bool: return len(self._errors) > 0
    
    def raise_if_errors(self, message: str = "Validation failed", sensitive_fields: frozenset[str] | None = None) -> None:
        if self._errors:
            raise ValidationError(message=message, details=self._errors.copy(), mode=ValidationMode.COLLECT_ALL, sensitive_fields=sensitive_fields)
    
    def clear(self) -> None: self._errors.clear()


def create_accumulator(mode: ValidationMode, max_errors: int = 50) -> ValidationErrorAccumulator:
    """Factory for creating accumulators based on mode."""
    return FailFastAccumulator() if mode == ValidationMode.FAIL_FAST else CollectAllAccumulator(max_errors=max_errors)


class ValidationContext:
    """Context manager for accumulating validation errors.
    
    Usage:
        with ValidationContext(mode=ValidationMode.COLLECT_ALL) as ctx:
            ctx.validate("email", email, EmailValidator())
            ctx.validate("age", age, NumericRange(min_value=0, max_value=150))
        # Raises ValidationError if any errors accumulated
    """
    
    def __init__(self, mode: ValidationMode = ValidationMode.FAIL_FAST, max_errors: int = 50,
                 sensitive_fields: frozenset[str] | None = None):
        self.accumulator, self.sensitive_fields, self._path_stack = create_accumulator(mode, max_errors), sensitive_fields, []
    
    def __enter__(self) -> ValidationContext: return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is None: self.accumulator.raise_if_errors(sensitive_fields=self.sensitive_fields)
        return False
    
    def push_path(self, segment: str | int) -> None: self._path_stack.append(str(segment))
    
    def pop_path(self) -> str | None: return self._path_stack.pop() if self._path_stack else None
    
    @property
    def current_path(self) -> str: return ".".join(self._path_stack) if self._path_stack else "$"
    
    def validate(self, field: str, value: Any, validator: "AtomicValidator") -> bool:
        """Validate a field and accumulate errors. Returns True if validation passed, False otherwise."""
        from .validators import AtomicValidator, ValidationResult
        
        if (result := validator.validate(value)).is_valid: return True
        full_path = f"{self.current_path}.{field}" if self._path_stack else field
        return self.accumulator.add_error(ValidationErrorDetail(field_path=full_path,
            constraint=result.constraint or validator.constraint_name, actual_value=result.actual,
            message=result.error_message or "Validation failed", suggested_fix=None))
    
    def add_error(self, field: str, message: str, *, constraint: str = "custom",
                  actual_value: Any = None, suggested_fix: str | None = None) -> bool:
        """Manually add a validation error."""
        full_path = f"{self.current_path}.{field}" if self._path_stack else field
        return self.accumulator.add_error(ValidationErrorDetail(field_path=full_path, constraint=constraint,
            actual_value=actual_value, message=message, suggested_fix=suggested_fix))
    
    @property
    def has_errors(self) -> bool: return self.accumulator.has_errors()
    
    @property
    def errors(self) -> list[ValidationErrorDetail]: return self.accumulator.get_errors()


# Avoid circular import
if False:
    from .validators import AtomicValidator
