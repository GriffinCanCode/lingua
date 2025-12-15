"""Compositional Validator System

Atomic validators combine via AND/OR/NOT combinators. Custom validators
integrate seamlessly with primitive combinators.

Features:
- Frozen dataclass validators for immutability
- Compiled regex caching
- Rich validation metadata for error context
- Lazy evaluation for OR combinators
- Short-circuit evaluation for AND combinators
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, TypeVar, Generic, Sequence
from dataclasses import dataclass, field
from functools import cached_property
import re
from uuid import UUID as StdUUID
from datetime import datetime, date, time
from decimal import Decimal
from ipaddress import IPv4Address, IPv6Address
from urllib.parse import urlparse
from email.utils import parseaddr

from core.errors import ErrorCode

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Result of a validation check with rich context."""
    is_valid: bool
    error_message: str | None = None
    error_code: ErrorCode | None = None
    constraint: str | None = None
    expected: Any = None
    actual: Any = None
    metadata: dict[str, Any] | None = None
    
    @classmethod
    def valid(cls) -> ValidationResult: return cls(is_valid=True)
    
    @classmethod
    def invalid(cls, message: str, code: ErrorCode = ErrorCode.E2000_VALIDATION_GENERIC, *,
                constraint: str | None = None, expected: Any = None, actual: Any = None, **metadata) -> ValidationResult:
        return cls(is_valid=False, error_message=message, error_code=code, constraint=constraint,
            expected=expected, actual=actual, metadata=metadata or None)
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize for API responses."""
        if self.is_valid: return {"valid": True}
        return {"valid": False, "message": self.error_message, "code": self.error_code.name if self.error_code else None,
            "constraint": self.constraint, "expected": self.expected, "actual": self.actual, **(self.metadata or {})}


class AtomicValidator(ABC):
    """Base class for atomic validators.
    
    Validators are immutable and composable via operators:
    - & (AND): both must pass
    - | (OR): at least one must pass
    - ~ (NOT): negates the validator
    """
    
    @abstractmethod
    def validate(self, value: Any) -> ValidationResult:
        """Validate a value. Returns ValidationResult."""
    
    @property
    @abstractmethod
    def constraint_name(self) -> str:
        """Human-readable constraint name for error messages."""
    
    def __call__(self, value: Any) -> ValidationResult: return self.validate(value)
    
    def __and__(self, other: AtomicValidator) -> And: return And(self, other)
    
    def __or__(self, other: AtomicValidator) -> Or: return Or(self, other)
    
    def __invert__(self) -> Not: return Not(self)
    
    def with_message(self, message: str) -> WithMessage: return WithMessage(self, message)


# ============================================================================
# String Validators
# ============================================================================

@dataclass(frozen=True, slots=True)
class StringLength(AtomicValidator):
    """Validate string length constraints."""
    min_length: int | None = None
    max_length: int | None = None
    
    @property
    def constraint_name(self) -> str:
        if self.min_length and self.max_length:
            return f"length[{self.min_length},{self.max_length}]"
        if self.min_length:
            return f"min_length[{self.min_length}]"
        if self.max_length:
            return f"max_length[{self.max_length}]"
        return "string_length"
    
    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, str):
            return ValidationResult.invalid(
                f"Expected string, got {type(value).__name__}",
                ErrorCode.E2004_INVALID_TYPE,
                constraint="string",
                expected="string",
                actual=type(value).__name__,
            )
        
        length = len(value)
        
        if self.min_length is not None and length < self.min_length:
            return ValidationResult.invalid(
                f"String length {length} is less than minimum {self.min_length}",
                ErrorCode.E2003_OUT_OF_RANGE,
                constraint=self.constraint_name,
                expected=f">= {self.min_length} characters",
                actual=f"{length} characters",
            )
        
        if self.max_length is not None and length > self.max_length:
            return ValidationResult.invalid(
                f"String length {length} exceeds maximum {self.max_length}",
                ErrorCode.E2003_OUT_OF_RANGE,
                constraint=self.constraint_name,
                expected=f"<= {self.max_length} characters",
                actual=f"{length} characters",
            )
        
        return ValidationResult.valid()


@dataclass(frozen=True, slots=True)
class NonEmpty(AtomicValidator):
    """Validate that string is not empty or whitespace-only."""
    strip_whitespace: bool = True
    
    @property
    def constraint_name(self) -> str:
        return "non_empty"
    
    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, str):
            return ValidationResult.invalid(
                f"Expected string, got {type(value).__name__}",
                ErrorCode.E2004_INVALID_TYPE,
                constraint="string",
            )
        
        check_value = value.strip() if self.strip_whitespace else value
        if not check_value:
            return ValidationResult.invalid(
                "String cannot be empty",
                ErrorCode.E2001_REQUIRED_FIELD_MISSING,
                constraint=self.constraint_name,
                expected="non-empty string",
                actual="empty string",
            )
        
        return ValidationResult.valid()


@dataclass(frozen=True, slots=True)
class RegexPattern(AtomicValidator):
    """Validate string against regex pattern."""
    pattern: str
    flags: int = 0
    description: str | None = None
    
    @cached_property
    def _compiled(self) -> re.Pattern:
        return re.compile(self.pattern, self.flags)
    
    @property
    def constraint_name(self) -> str:
        return self.description or f"pattern[{self.pattern}]"
    
    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, str):
            return ValidationResult.invalid(
                f"Expected string, got {type(value).__name__}",
                ErrorCode.E2004_INVALID_TYPE,
                constraint="string",
            )
        
        if not self._compiled.match(value):
            return ValidationResult.invalid(
                f"Value does not match pattern: {self.description or self.pattern}",
                ErrorCode.E2002_INVALID_FORMAT,
                constraint=self.constraint_name,
                expected=f"match pattern '{self.pattern}'",
                actual=value[:50] + ("..." if len(value) > 50 else ""),
            )
        
        return ValidationResult.valid()


@dataclass(frozen=True, slots=True)
class OneOf(AtomicValidator):
    """Validate value is one of allowed options."""
    options: frozenset[str]
    case_sensitive: bool = True
    
    def __init__(self, *options: str, case_sensitive: bool = True):
        object.__setattr__(self, "options", frozenset(options)); object.__setattr__(self, "case_sensitive", case_sensitive)
    
    @property
    def constraint_name(self) -> str:
        opts = sorted(self.options)[:5]
        suffix = f"... +{len(self.options) - 5}" if len(self.options) > 5 else ""
        return f"one_of[{', '.join(opts)}{suffix}]"
    
    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, str):
            return ValidationResult.invalid(f"Expected string, got {type(value).__name__}",
                ErrorCode.E2004_INVALID_TYPE, constraint="string")
        
        check_value = value if self.case_sensitive else value.lower()
        check_options = self.options if self.case_sensitive else frozenset(o.lower() for o in self.options)
        
        if check_value not in check_options:
            return ValidationResult.invalid(f"Value '{value}' is not one of: {', '.join(sorted(self.options))}",
                ErrorCode.E2005_CONSTRAINT_VIOLATION, constraint=self.constraint_name,
                expected=list(sorted(self.options)), actual=value)
        return ValidationResult.valid()


# ============================================================================
# Numeric Validators
# ============================================================================

@dataclass(frozen=True, slots=True)
class NumericRange(AtomicValidator):
    """Validate numeric range constraints."""
    min_value: float | int | None = None
    max_value: float | int | None = None
    exclusive_min: bool = False
    exclusive_max: bool = False
    
    @property
    def constraint_name(self) -> str:
        parts = []
        if self.min_value is not None:
            op = ">" if self.exclusive_min else ">="
            parts.append(f"{op}{self.min_value}")
        if self.max_value is not None:
            op = "<" if self.exclusive_max else "<="
            parts.append(f"{op}{self.max_value}")
        return f"range[{', '.join(parts)}]" if parts else "numeric"
    
    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, (int, float, Decimal)):
            return ValidationResult.invalid(
                f"Expected number, got {type(value).__name__}",
                ErrorCode.E2004_INVALID_TYPE,
                constraint="numeric",
                expected="number",
                actual=type(value).__name__,
            )
        
        num = float(value)
        
        if self.min_value is not None:
            if self.exclusive_min and num <= self.min_value:
                return ValidationResult.invalid(
                    f"Value {num} must be greater than {self.min_value}",
                    ErrorCode.E2003_OUT_OF_RANGE,
                    constraint=self.constraint_name,
                    expected=f"> {self.min_value}",
                    actual=num,
                )
            elif not self.exclusive_min and num < self.min_value:
                return ValidationResult.invalid(
                    f"Value {num} must be at least {self.min_value}",
                    ErrorCode.E2003_OUT_OF_RANGE,
                    constraint=self.constraint_name,
                    expected=f">= {self.min_value}",
                    actual=num,
                )
        
        if self.max_value is not None:
            if self.exclusive_max and num >= self.max_value:
                return ValidationResult.invalid(
                    f"Value {num} must be less than {self.max_value}",
                    ErrorCode.E2003_OUT_OF_RANGE,
                    constraint=self.constraint_name,
                    expected=f"< {self.max_value}",
                    actual=num,
                )
            elif not self.exclusive_max and num > self.max_value:
                return ValidationResult.invalid(
                    f"Value {num} must be at most {self.max_value}",
                    ErrorCode.E2003_OUT_OF_RANGE,
                    constraint=self.constraint_name,
                    expected=f"<= {self.max_value}",
                    actual=num,
                )
        
        return ValidationResult.valid()


@dataclass(frozen=True, slots=True)
class MultipleOf(AtomicValidator):
    """Validate number is multiple of value."""
    factor: float | int
    
    @property
    def constraint_name(self) -> str:
        return f"multiple_of[{self.factor}]"
    
    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, (int, float, Decimal)):
            return ValidationResult.invalid(
                f"Expected number, got {type(value).__name__}",
                ErrorCode.E2004_INVALID_TYPE,
                constraint="numeric",
            )
        
        remainder = float(value) % float(self.factor)
        if remainder != 0 and abs(remainder) > 1e-9:
            return ValidationResult.invalid(
                f"Value {value} must be a multiple of {self.factor}",
                ErrorCode.E2005_CONSTRAINT_VIOLATION,
                constraint=self.constraint_name,
                expected=f"multiple of {self.factor}",
                actual=value,
            )
        
        return ValidationResult.valid()


@dataclass(frozen=True, slots=True)
class Positive(AtomicValidator):
    """Validate number is positive (> 0)."""
    
    @property
    def constraint_name(self) -> str:
        return "positive"
    
    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, (int, float, Decimal)):
            return ValidationResult.invalid(
                f"Expected number, got {type(value).__name__}",
                ErrorCode.E2004_INVALID_TYPE,
                constraint="numeric",
            )
        
        if value <= 0:
            return ValidationResult.invalid(
                f"Value {value} must be positive",
                ErrorCode.E2003_OUT_OF_RANGE,
                constraint=self.constraint_name,
                expected="> 0",
                actual=value,
            )
        
        return ValidationResult.valid()


@dataclass(frozen=True, slots=True)
class NonNegative(AtomicValidator):
    """Validate number is non-negative (>= 0)."""
    
    @property
    def constraint_name(self) -> str:
        return "non_negative"
    
    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, (int, float, Decimal)):
            return ValidationResult.invalid(
                f"Expected number, got {type(value).__name__}",
                ErrorCode.E2004_INVALID_TYPE,
                constraint="numeric",
            )
        
        if value < 0:
            return ValidationResult.invalid(
                f"Value {value} cannot be negative",
                ErrorCode.E2003_OUT_OF_RANGE,
                constraint=self.constraint_name,
                expected=">= 0",
                actual=value,
            )
        
        return ValidationResult.valid()


# ============================================================================
# Format Validators
# ============================================================================

@dataclass(frozen=True, slots=True)
class EmailValidator(AtomicValidator):
    """Validate email address format."""
    allow_display_name: bool = False
    
    @property
    def constraint_name(self) -> str:
        return "email"
    
    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, str):
            return ValidationResult.invalid(
                f"Expected string, got {type(value).__name__}",
                ErrorCode.E2004_INVALID_TYPE,
                constraint="string",
            )
        
        # RFC 5322 simplified pattern
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        name, addr = parseaddr(value)
        check_value = addr if self.allow_display_name else value
        
        if not check_value or not re.match(pattern, check_value):
            return ValidationResult.invalid(
                f"Invalid email format: {value}",
                ErrorCode.E2010_INVALID_EMAIL,
                constraint=self.constraint_name,
                expected="valid email address",
                actual=value,
            )
        
        return ValidationResult.valid()


@dataclass(frozen=True, slots=True)
class UUIDValidator(AtomicValidator):
    """Validate UUID format."""
    version: int | None = None
    
    @property
    def constraint_name(self) -> str:
        return f"uuid{f'v{self.version}' if self.version else ''}"
    
    def validate(self, value: Any) -> ValidationResult:
        if isinstance(value, StdUUID):
            if self.version and value.version != self.version:
                return ValidationResult.invalid(
                    f"Expected UUID version {self.version}, got version {value.version}",
                    ErrorCode.E2011_INVALID_UUID,
                    constraint=self.constraint_name,
                    expected=f"UUID v{self.version}",
                    actual=f"UUID v{value.version}",
                )
            return ValidationResult.valid()
        
        if not isinstance(value, str):
            return ValidationResult.invalid(
                f"Expected UUID string, got {type(value).__name__}",
                ErrorCode.E2004_INVALID_TYPE,
                constraint="uuid",
            )
        
        try:
            parsed = StdUUID(value)
            if self.version and parsed.version != self.version:
                return ValidationResult.invalid(
                    f"Expected UUID version {self.version}, got version {parsed.version}",
                    ErrorCode.E2011_INVALID_UUID,
                    constraint=self.constraint_name,
                )
            return ValidationResult.valid()
        except ValueError:
            return ValidationResult.invalid(
                f"Invalid UUID format: {value}",
                ErrorCode.E2011_INVALID_UUID,
                constraint=self.constraint_name,
                expected="valid UUID",
                actual=value[:50] if len(value) > 50 else value,
            )


@dataclass(frozen=True, slots=True)
class DateTimeValidator(AtomicValidator):
    """Validate ISO8601 datetime format."""
    require_timezone: bool = False
    
    @property
    def constraint_name(self) -> str:
        return "datetime" + ("_tz" if self.require_timezone else "")
    
    def validate(self, value: Any) -> ValidationResult:
        if isinstance(value, datetime):
            if self.require_timezone and value.tzinfo is None:
                return ValidationResult.invalid(
                    "Datetime must include timezone",
                    ErrorCode.E2012_INVALID_DATE,
                    constraint=self.constraint_name,
                    expected="datetime with timezone",
                    actual="datetime without timezone",
                )
            return ValidationResult.valid()
        
        if not isinstance(value, str):
            return ValidationResult.invalid(
                f"Expected datetime string, got {type(value).__name__}",
                ErrorCode.E2004_INVALID_TYPE,
                constraint="datetime",
            )
        
        try:
            normalized = value.replace('Z', '+00:00')
            dt = datetime.fromisoformat(normalized)
            if self.require_timezone and dt.tzinfo is None:
                return ValidationResult.invalid(
                    "Datetime must include timezone",
                    ErrorCode.E2012_INVALID_DATE,
                    constraint=self.constraint_name,
                )
            return ValidationResult.valid()
        except (ValueError, AttributeError):
            return ValidationResult.invalid(
                f"Invalid ISO8601 datetime: {value}",
                ErrorCode.E2012_INVALID_DATE,
                constraint=self.constraint_name,
                expected="ISO8601 datetime",
                actual=value,
            )


@dataclass(frozen=True, slots=True)
class URLValidator(AtomicValidator):
    """Validate URL format."""
    allowed_schemes: frozenset[str] = frozenset({"http", "https"})
    require_tld: bool = True
    
    def __init__(self, allowed_schemes: Sequence[str] = ("http", "https"), require_tld: bool = True):
        object.__setattr__(self, "allowed_schemes", frozenset(allowed_schemes)); object.__setattr__(self, "require_tld", require_tld)
    
    @property
    def constraint_name(self) -> str:
        return f"url[{', '.join(sorted(self.allowed_schemes))}]"
    
    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, str):
            return ValidationResult.invalid(
                f"Expected string, got {type(value).__name__}",
                ErrorCode.E2004_INVALID_TYPE,
                constraint="string",
            )
        
        try:
            parsed = urlparse(value)
            
            if not parsed.scheme:
                return ValidationResult.invalid(
                    "URL must include scheme (e.g., https://)",
                    ErrorCode.E2002_INVALID_FORMAT,
                    constraint=self.constraint_name,
                    expected="URL with scheme",
                    actual=value,
                )
            
            if parsed.scheme not in self.allowed_schemes:
                return ValidationResult.invalid(
                    f"URL scheme '{parsed.scheme}' not allowed",
                    ErrorCode.E2002_INVALID_FORMAT,
                    constraint=self.constraint_name,
                    expected=f"scheme in {list(self.allowed_schemes)}",
                    actual=parsed.scheme,
                )
            
            if not parsed.netloc:
                return ValidationResult.invalid(
                    "URL must include host",
                    ErrorCode.E2002_INVALID_FORMAT,
                    constraint=self.constraint_name,
                    expected="URL with host",
                    actual=value,
                )
            
            if self.require_tld and "." not in parsed.netloc.split(":")[0]:
                return ValidationResult.invalid(
                    "URL host must include TLD",
                    ErrorCode.E2002_INVALID_FORMAT,
                    constraint=self.constraint_name,
                    expected="URL with TLD (e.g., .com)",
                    actual=parsed.netloc,
                )
            
            return ValidationResult.valid()
        except Exception:
            return ValidationResult.invalid(
                f"Invalid URL: {value}",
                ErrorCode.E2002_INVALID_FORMAT,
                constraint=self.constraint_name,
                expected="valid URL",
                actual=value[:50] if len(value) > 50 else value,
            )


@dataclass(frozen=True, slots=True)
class IPAddressValidator(AtomicValidator):
    """Validate IP address format."""
    version: int | None = None  # 4 or 6, None for both
    
    @property
    def constraint_name(self) -> str:
        return f"ip{f'v{self.version}' if self.version else ''}"
    
    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, str):
            return ValidationResult.invalid(
                f"Expected string, got {type(value).__name__}",
                ErrorCode.E2004_INVALID_TYPE,
                constraint="string",
            )
        
        try:
            if self.version == 4:
                IPv4Address(value)
            elif self.version == 6:
                IPv6Address(value)
            else:
                try:
                    IPv4Address(value)
                except ValueError:
                    IPv6Address(value)
            return ValidationResult.valid()
        except ValueError:
            expected = f"IPv{self.version}" if self.version else "IP address"
            return ValidationResult.invalid(
                f"Invalid {expected}: {value}",
                ErrorCode.E2002_INVALID_FORMAT,
                constraint=self.constraint_name,
                expected=expected,
                actual=value,
            )


# ============================================================================
# Collection Validators
# ============================================================================

@dataclass(frozen=True, slots=True)
class ListLength(AtomicValidator):
    """Validate list/array length constraints."""
    min_length: int | None = None
    max_length: int | None = None
    
    @property
    def constraint_name(self) -> str:
        parts = []
        if self.min_length is not None:
            parts.append(f"min={self.min_length}")
        if self.max_length is not None:
            parts.append(f"max={self.max_length}")
        return f"list_length[{', '.join(parts)}]" if parts else "list"
    
    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, (list, tuple)):
            return ValidationResult.invalid(
                f"Expected list, got {type(value).__name__}",
                ErrorCode.E2004_INVALID_TYPE,
                constraint="list",
                expected="list",
                actual=type(value).__name__,
            )
        
        length = len(value)
        
        if self.min_length is not None and length < self.min_length:
            return ValidationResult.invalid(
                f"List has {length} items, minimum is {self.min_length}",
                ErrorCode.E2003_OUT_OF_RANGE,
                constraint=self.constraint_name,
                expected=f">= {self.min_length} items",
                actual=f"{length} items",
            )
        
        if self.max_length is not None and length > self.max_length:
            return ValidationResult.invalid(
                f"List has {length} items, maximum is {self.max_length}",
                ErrorCode.E2003_OUT_OF_RANGE,
                constraint=self.constraint_name,
                expected=f"<= {self.max_length} items",
                actual=f"{length} items",
            )
        
        return ValidationResult.valid()


@dataclass(frozen=True, slots=True)
class UniqueItems(AtomicValidator):
    """Validate list contains unique items."""
    
    @property
    def constraint_name(self) -> str:
        return "unique_items"
    
    def validate(self, value: Any) -> ValidationResult:
        if not isinstance(value, (list, tuple)):
            return ValidationResult.invalid(
                f"Expected list, got {type(value).__name__}",
                ErrorCode.E2004_INVALID_TYPE,
                constraint="list",
            )
        
        seen: set = set()
        duplicates = []
        for item in value:
            try:
                hashable = item if isinstance(item, (str, int, float, bool, type(None))) else str(item)
                if hashable in seen:
                    duplicates.append(item)
                seen.add(hashable)
            except TypeError:
                continue
        
        if duplicates:
            return ValidationResult.invalid(
                f"List contains duplicate items: {duplicates[:3]}",
                ErrorCode.E2005_CONSTRAINT_VIOLATION,
                constraint=self.constraint_name,
                expected="unique items",
                actual=f"duplicates: {duplicates[:3]}",
            )
        
        return ValidationResult.valid()


# ============================================================================
# Combinators
# ============================================================================

@dataclass(frozen=True, slots=True)
class And(AtomicValidator):
    """AND combinator: all validators must pass (short-circuit on first failure)."""
    left: AtomicValidator
    right: AtomicValidator
    
    @property
    def constraint_name(self) -> str:
        return f"({self.left.constraint_name} AND {self.right.constraint_name})"
    
    def validate(self, value: Any) -> ValidationResult:
        if not (left_result := self.left.validate(value)).is_valid: return left_result
        return self.right.validate(value)
    
    def __and__(self, other: AtomicValidator) -> And: return And(self, other)


@dataclass(frozen=True, slots=True)
class Or(AtomicValidator):
    """OR combinator: at least one validator must pass (lazy evaluation)."""
    left: AtomicValidator
    right: AtomicValidator
    
    @property
    def constraint_name(self) -> str:
        return f"({self.left.constraint_name} OR {self.right.constraint_name})"
    
    def validate(self, value: Any) -> ValidationResult:
        if (left_result := self.left.validate(value)).is_valid: return ValidationResult.valid()
        if (right_result := self.right.validate(value)).is_valid: return ValidationResult.valid()
        return ValidationResult.invalid(f"Neither constraint satisfied: {left_result.error_message} OR {right_result.error_message}",
            ErrorCode.E2000_VALIDATION_GENERIC, constraint=self.constraint_name,
            left_error=left_result.error_message, right_error=right_result.error_message)
    
    def __or__(self, other: AtomicValidator) -> Or: return Or(self, other)


@dataclass(frozen=True, slots=True)
class Not(AtomicValidator):
    """NOT combinator: negates validator."""
    validator: AtomicValidator
    message: str | None = None
    
    @property
    def constraint_name(self) -> str:
        return f"NOT({self.validator.constraint_name})"
    
    def validate(self, value: Any) -> ValidationResult:
        if (result := self.validator.validate(value)).is_valid:
            return ValidationResult.invalid(self.message or f"Value should not satisfy: {self.validator.constraint_name}",
                ErrorCode.E2005_CONSTRAINT_VIOLATION, constraint=self.constraint_name)
        return ValidationResult.valid()


@dataclass(frozen=True, slots=True)
class WithMessage(AtomicValidator):
    """Wrapper to override error message."""
    validator: AtomicValidator
    message: str
    
    @property
    def constraint_name(self) -> str:
        return self.validator.constraint_name
    
    def validate(self, value: Any) -> ValidationResult:
        if (result := self.validator.validate(value)).is_valid: return result
        return ValidationResult.invalid(self.message, result.error_code or ErrorCode.E2000_VALIDATION_GENERIC,
            constraint=result.constraint, expected=result.expected, actual=result.actual)


@dataclass(frozen=True, slots=True)
class AllOf(AtomicValidator):
    """All validators must pass."""
    validators: tuple[AtomicValidator, ...]
    
    def __init__(self, *validators: AtomicValidator):
        object.__setattr__(self, "validators", tuple(validators))
    
    @property
    def constraint_name(self) -> str:
        return f"all_of[{', '.join(v.constraint_name for v in self.validators)}]"
    
    def validate(self, value: Any) -> ValidationResult:
        for v in self.validators:
            if not (result := v.validate(value)).is_valid: return result
        return ValidationResult.valid()


@dataclass(frozen=True, slots=True)
class AnyOf(AtomicValidator):
    """At least one validator must pass."""
    validators: tuple[AtomicValidator, ...]
    
    def __init__(self, *validators: AtomicValidator):
        object.__setattr__(self, "validators", tuple(validators))
    
    @property
    def constraint_name(self) -> str:
        return f"any_of[{', '.join(v.constraint_name for v in self.validators)}]"
    
    def validate(self, value: Any) -> ValidationResult:
        errors = []
        for v in self.validators:
            if (result := v.validate(value)).is_valid: return ValidationResult.valid()
            errors.append(result.error_message)
        return ValidationResult.invalid(f"No constraint satisfied: {'; '.join(e or '' for e in errors)}",
            ErrorCode.E2000_VALIDATION_GENERIC, constraint=self.constraint_name)


# ============================================================================
# Custom Validator
# ============================================================================

@dataclass(frozen=True, slots=True)
class CustomValidator(AtomicValidator):
    """Custom validator from function.
    
    Usage:
        def is_even(n: int) -> ValidationResult:
            if n % 2 != 0:
                return ValidationResult.invalid("Must be even")
            return ValidationResult.valid()
        
        validator = CustomValidator(is_even, name="even")
    """
    validator_fn: Callable[[Any], ValidationResult]
    name: str = "custom"
    
    @property
    def constraint_name(self) -> str:
        return self.name
    
    def validate(self, value: Any) -> ValidationResult:
        try: return self.validator_fn(value)
        except Exception as e:
            return ValidationResult.invalid(f"Validation error: {e}", ErrorCode.E2000_VALIDATION_GENERIC,
                constraint=self.name, exception=str(e))


def custom(name: str) -> Callable[[Callable[[Any], ValidationResult]], CustomValidator]:
    """Decorator to create custom validator from function.
    
    Usage:
        @custom("even")
        def is_even(n: int) -> ValidationResult:
            if n % 2 != 0:
                return ValidationResult.invalid("Must be even")
            return ValidationResult.valid()
    """
    return lambda fn: CustomValidator(fn, name=name)
