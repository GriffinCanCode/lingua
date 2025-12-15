"""Annotated Type Validators for Declarative Field Constraints

Use Python's Annotated type hint with Pydantic v2 for declarative,
composable validation. Validators run in order and can be combined.

Usage:
    from core.validation.annotated import (
        Trimmed, NonEmpty, LowerCase, Email, Slug,
        Positive, NonNegative, Percentage,
        ValidatedStr, ValidatedInt,
    )
    
    class UserCreate(BaseSchema):
        email: Email
        username: Annotated[str, Trimmed, LowerCase, NonEmpty, MinLen(3), MaxLen(50)]
        age: Annotated[int, Positive, Max(150)]
        score: Percentage
"""
from __future__ import annotations

from typing import Annotated, Any, Callable, TypeVar
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from uuid import UUID
import re
from functools import lru_cache

from pydantic import (
    BeforeValidator,
    AfterValidator,
    PlainValidator,
    WrapValidator,
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
)
from pydantic_core import CoreSchema, core_schema
from pydantic.json_schema import JsonSchemaValue

T = TypeVar("T")


# ============================================================================
# String Transformers (BeforeValidator - run before type coercion)
# ============================================================================

_trim = lambda v: v.strip() if isinstance(v, str) else v
_lower = lambda v: v.lower() if isinstance(v, str) else v
_upper = lambda v: v.upper() if isinstance(v, str) else v
_title = lambda v: v.title() if isinstance(v, str) else v
_normalize_whitespace = lambda v: " ".join(v.split()) if isinstance(v, str) else v
_remove_control_chars = lambda v: "".join(c for c in v if c.isprintable() or c in "\n\t") if isinstance(v, str) else v

Trimmed = BeforeValidator(_trim)
LowerCase = BeforeValidator(_lower)
UpperCase = BeforeValidator(_upper)
TitleCase = BeforeValidator(_title)
NormalizedWhitespace = BeforeValidator(_normalize_whitespace)
SafeString = BeforeValidator(_remove_control_chars)


# ============================================================================
# String Validators (AfterValidator - run after type coercion)
# ============================================================================

def _non_empty(v: str) -> str:
    """Validate string is not empty after trimming."""
    if not v.strip(): raise ValueError("String cannot be empty or whitespace-only")
    return v

def _ascii_only(v: str) -> str:
    """Validate string contains only ASCII characters."""
    if not v.isascii(): raise ValueError("String must contain only ASCII characters")
    return v

def _alphanumeric(v: str) -> str:
    """Validate string is alphanumeric."""
    if not v.replace(" ", "").replace("_", "").replace("-", "").isalnum():
        raise ValueError("String must be alphanumeric (with optional spaces, underscores, hyphens)")
    return v

def _slug_format(v: str) -> str:
    """Validate slug format (lowercase alphanumeric with hyphens)."""
    if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", v):
        raise ValueError("Invalid slug: must be lowercase alphanumeric with hyphens")
    return v

def _email_format(v: str) -> str:
    """Validate email format."""
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
        raise ValueError(f"Invalid email format: {v}")
    return v

def _uuid_format(v: str) -> str:
    """Validate UUID format (passthrough if already UUID)."""
    try: UUID(v); return v
    except (ValueError, AttributeError): raise ValueError(f"Invalid UUID format: {v}")


NonEmpty = AfterValidator(_non_empty)
AsciiOnly = AfterValidator(_ascii_only)
AlphaNumeric = AfterValidator(_alphanumeric)
SlugFormat = AfterValidator(_slug_format)
EmailFormat = AfterValidator(_email_format)
UUIDFormat = AfterValidator(_uuid_format)


# ============================================================================
# Length Validators
# ============================================================================

class MinLen:
    """Minimum length validator factory."""
    __slots__ = ("min_length",)
    
    def __init__(self, min_length: int): self.min_length = min_length
    
    def __get_pydantic_core_schema__(self, source_type: type, handler: GetCoreSchemaHandler) -> CoreSchema:
        return core_schema.no_info_after_validator_function(self._validate, handler(source_type))
    
    def _validate(self, v: Any) -> Any:
        if hasattr(v, "__len__") and len(v) < self.min_length:
            raise ValueError(f"Length must be at least {self.min_length}, got {len(v)}")
        return v
    
    def __get_pydantic_json_schema__(self, core_schema: CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        return {**handler(core_schema), "minLength": self.min_length}


class MaxLen:
    """Maximum length validator factory."""
    __slots__ = ("max_length",)
    
    def __init__(self, max_length: int): self.max_length = max_length
    
    def __get_pydantic_core_schema__(self, source_type: type, handler: GetCoreSchemaHandler) -> CoreSchema:
        return core_schema.no_info_after_validator_function(self._validate, handler(source_type))
    
    def _validate(self, v: Any) -> Any:
        if hasattr(v, "__len__") and len(v) > self.max_length:
            raise ValueError(f"Length must be at most {self.max_length}, got {len(v)}")
        return v
    
    def __get_pydantic_json_schema__(self, core_schema: CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        return {**handler(core_schema), "maxLength": self.max_length}


class Pattern:
    """Regex pattern validator factory."""
    __slots__ = ("pattern", "description", "_compiled")
    
    def __init__(self, pattern: str, description: str | None = None):
        self.pattern, self.description, self._compiled = pattern, description or pattern, re.compile(pattern)
    
    def __get_pydantic_core_schema__(self, source_type: type, handler: GetCoreSchemaHandler) -> CoreSchema:
        return core_schema.no_info_after_validator_function(self._validate, handler(source_type))
    
    def _validate(self, v: str) -> str:
        if not self._compiled.match(v): raise ValueError(f"Value must match pattern: {self.description}")
        return v
    
    def __get_pydantic_json_schema__(self, core_schema: CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        return {**handler(core_schema), "pattern": self.pattern}


# ============================================================================
# Numeric Validators
# ============================================================================

class Gt:
    """Greater than validator factory."""
    __slots__ = ("value",)
    
    def __init__(self, value: float | int): self.value = value
    
    def __get_pydantic_core_schema__(self, source_type: type, handler: GetCoreSchemaHandler) -> CoreSchema:
        return core_schema.no_info_after_validator_function(self._validate, handler(source_type))
    
    def _validate(self, v: float | int) -> float | int:
        if v <= self.value: raise ValueError(f"Value must be greater than {self.value}")
        return v
    
    def __get_pydantic_json_schema__(self, core_schema: CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        return {**handler(core_schema), "exclusiveMinimum": self.value}


class Ge:
    """Greater than or equal validator factory."""
    __slots__ = ("value",)
    
    def __init__(self, value: float | int): self.value = value
    
    def __get_pydantic_core_schema__(self, source_type: type, handler: GetCoreSchemaHandler) -> CoreSchema:
        return core_schema.no_info_after_validator_function(self._validate, handler(source_type))
    
    def _validate(self, v: float | int) -> float | int:
        if v < self.value: raise ValueError(f"Value must be at least {self.value}")
        return v
    
    def __get_pydantic_json_schema__(self, core_schema: CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        return {**handler(core_schema), "minimum": self.value}


class Lt:
    """Less than validator factory."""
    __slots__ = ("value",)
    
    def __init__(self, value: float | int): self.value = value
    
    def __get_pydantic_core_schema__(self, source_type: type, handler: GetCoreSchemaHandler) -> CoreSchema:
        return core_schema.no_info_after_validator_function(self._validate, handler(source_type))
    
    def _validate(self, v: float | int) -> float | int:
        if v >= self.value: raise ValueError(f"Value must be less than {self.value}")
        return v
    
    def __get_pydantic_json_schema__(self, core_schema: CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        return {**handler(core_schema), "exclusiveMaximum": self.value}


class Le:
    """Less than or equal validator factory."""
    __slots__ = ("value",)
    
    def __init__(self, value: float | int): self.value = value
    
    def __get_pydantic_core_schema__(self, source_type: type, handler: GetCoreSchemaHandler) -> CoreSchema:
        return core_schema.no_info_after_validator_function(self._validate, handler(source_type))
    
    def _validate(self, v: float | int) -> float | int:
        if v > self.value: raise ValueError(f"Value must be at most {self.value}")
        return v
    
    def __get_pydantic_json_schema__(self, core_schema: CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        return {**handler(core_schema), "maximum": self.value}


class MultipleOf:
    """Multiple of validator factory."""
    __slots__ = ("factor",)
    
    def __init__(self, factor: float | int): self.factor = factor
    
    def __get_pydantic_core_schema__(self, source_type: type, handler: GetCoreSchemaHandler) -> CoreSchema:
        return core_schema.no_info_after_validator_function(self._validate, handler(source_type))
    
    def _validate(self, v: float | int) -> float | int:
        if (r := float(v) % float(self.factor)) != 0 and abs(r) > 1e-9:
            raise ValueError(f"Value must be a multiple of {self.factor}")
        return v
    
    def __get_pydantic_json_schema__(self, core_schema: CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        return {**handler(core_schema), "multipleOf": self.factor}


def _positive(v: float | int | Decimal) -> float | int | Decimal:
    """Validate value is positive."""
    if v <= 0: raise ValueError("Value must be positive (> 0)")
    return v

def _non_negative(v: float | int | Decimal) -> float | int | Decimal:
    """Validate value is non-negative."""
    if v < 0: raise ValueError("Value must be non-negative (>= 0)")
    return v

def _percentage(v: float | int | Decimal) -> float | int | Decimal:
    """Validate value is a percentage (0-100)."""
    if not 0 <= v <= 100: raise ValueError("Value must be between 0 and 100")
    return v

def _rating(v: int) -> int:
    """Validate value is a rating (0-5)."""
    if not 0 <= v <= 5: raise ValueError("Rating must be between 0 and 5")
    return v


Positive = AfterValidator(_positive)
NonNegative = AfterValidator(_non_negative)
PercentageRange = AfterValidator(_percentage)
RatingRange = AfterValidator(_rating)


# ============================================================================
# DateTime Validators
# ============================================================================

def _past_datetime(v: datetime) -> datetime:
    """Validate datetime is in the past."""
    if v > datetime.now(v.tzinfo): raise ValueError("Datetime must be in the past")
    return v

def _future_datetime(v: datetime) -> datetime:
    """Validate datetime is in the future."""
    if v < datetime.now(v.tzinfo): raise ValueError("Datetime must be in the future")
    return v

def _timezone_aware(v: datetime) -> datetime:
    """Validate datetime has timezone info."""
    if v.tzinfo is None: raise ValueError("Datetime must be timezone-aware")
    return v

PastDateTime = AfterValidator(_past_datetime)
FutureDateTime = AfterValidator(_future_datetime)
TimezoneAware = AfterValidator(_timezone_aware)


# ============================================================================
# Collection Validators
# ============================================================================

class MinItems:
    """Minimum items validator factory for lists."""
    __slots__ = ("min_items",)
    
    def __init__(self, min_items: int): self.min_items = min_items
    
    def __get_pydantic_core_schema__(self, source_type: type, handler: GetCoreSchemaHandler) -> CoreSchema:
        return core_schema.no_info_after_validator_function(self._validate, handler(source_type))
    
    def _validate(self, v: list) -> list:
        if len(v) < self.min_items: raise ValueError(f"List must have at least {self.min_items} items")
        return v
    
    def __get_pydantic_json_schema__(self, core_schema: CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        return {**handler(core_schema), "minItems": self.min_items}


class MaxItems:
    """Maximum items validator factory for lists."""
    __slots__ = ("max_items",)
    
    def __init__(self, max_items: int): self.max_items = max_items
    
    def __get_pydantic_core_schema__(self, source_type: type, handler: GetCoreSchemaHandler) -> CoreSchema:
        return core_schema.no_info_after_validator_function(self._validate, handler(source_type))
    
    def _validate(self, v: list) -> list:
        if len(v) > self.max_items: raise ValueError(f"List must have at most {self.max_items} items")
        return v
    
    def __get_pydantic_json_schema__(self, core_schema: CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        return {**handler(core_schema), "maxItems": self.max_items}


def _unique_items(v: list) -> list:
    """Validate list contains unique items."""
    seen: set = set()
    for item in v:
        try:
            key = item if isinstance(item, (str, int, float, bool, type(None))) else str(item)
            if key in seen: raise ValueError(f"List contains duplicate item: {item}")
            seen.add(key)
        except TypeError: continue
    return v

UniqueItems = AfterValidator(_unique_items)


# ============================================================================
# Pre-built Annotated Types
# ============================================================================

# Strings
TrimmedStr = Annotated[str, Trimmed]
NonEmptyStr = Annotated[str, Trimmed, NonEmpty]
Email = Annotated[str, Trimmed, LowerCase, EmailFormat]
Slug = Annotated[str, Trimmed, LowerCase, SlugFormat]
Username = Annotated[str, Trimmed, LowerCase, MinLen(3), MaxLen(50), AlphaNumeric]

# Numbers
PositiveInt = Annotated[int, Positive]
NonNegativeInt = Annotated[int, NonNegative]
PositiveFloat = Annotated[float, Positive]
NonNegativeFloat = Annotated[float, NonNegative]
Percentage = Annotated[float, PercentageRange]
Rating = Annotated[int, RatingRange]

# DateTime
PastDatetime = Annotated[datetime, PastDateTime]
FutureDatetime = Annotated[datetime, FutureDateTime]
TzAwareDatetime = Annotated[datetime, TimezoneAware]

# Language
LanguageCode = Annotated[str, Trimmed, LowerCase, Pattern(r"^[a-z]{2,3}(-[A-Z]{2})?$", "language code")]


# ============================================================================
# Custom Validator Decorator
# ============================================================================

def validator(*, pre: bool = False, always: bool = True) -> Callable[[Callable[[T], T]], Any]:
    """Decorator to create a Pydantic validator from a function.
    
    Usage:
        @validator()
        def is_even(n: int) -> int:
            if n % 2 != 0:
                raise ValueError("Must be even")
            return n
        
        class MyModel(BaseSchema):
            count: Annotated[int, is_even]
    """
    return lambda fn: BeforeValidator(fn) if pre else AfterValidator(fn)

