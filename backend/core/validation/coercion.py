"""Explicit Opt-in Coercion System

Coercion rules are explicit and opt-in, NEVER implicit. Each coercion
must be explicitly enabled at the field or schema level.

Features:
- Type-safe coercion with Result types
- Extensible rule registry
- JSON Schema generation for coerced types
- No silent data loss or implicit conversions
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypeVar, Callable, Generic, Sequence, Annotated
from dataclasses import dataclass, field
from datetime import datetime, date, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
from uuid import UUID
from enum import Enum
import re

from pydantic import BeforeValidator, GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic_core import CoreSchema, core_schema
from pydantic.json_schema import JsonSchemaValue

from core.errors import AppError, ErrorCode, Ok, Err, Result

T = TypeVar("T")
S = TypeVar("S")


@dataclass(frozen=True, slots=True)
class CoercionRule(ABC, Generic[S, T]):
    """Base class for coercion rules.
    
    Each rule defines:
    - Source type(s) it can coerce from
    - Target type it coerces to
    - Validation of coercion feasibility
    - The actual coercion logic
    """
    
    @property
    @abstractmethod
    def source_types(self) -> tuple[type, ...]:
        """Types this rule can coerce from."""
    
    @property
    @abstractmethod
    def target_type(self) -> type[T]:
        """Type this rule coerces to."""
    
    @abstractmethod
    def can_coerce(self, value: Any) -> bool:
        """Check if value can be coerced to target type."""
    
    @abstractmethod
    def coerce(self, value: Any) -> Result[T, AppError]:
        """Coerce value to target type. Returns Result."""
    
    def __call__(self, value: Any) -> Result[T, AppError]:
        return self.coerce(value)


@dataclass(frozen=True, slots=True)
class StringToInt(CoercionRule[str, int]):
    """Coerce string to integer."""
    allow_float_strings: bool = False
    
    @property
    def source_types(self) -> tuple[type, ...]:
        return (str,)
    
    @property
    def target_type(self) -> type[int]:
        return int
    
    def can_coerce(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        stripped = value.strip()
        if not stripped:
            return False
        try:
            if self.allow_float_strings:
                float(stripped)
            else:
                int(stripped)
            return True
        except ValueError:
            return False
    
    def coerce(self, value: Any) -> Result[int, AppError]:
        if not isinstance(value, str):
            return Err(AppError(
                code=ErrorCode.E2004_INVALID_TYPE,
                message=f"Cannot coerce {type(value).__name__} to int",
            ))
        
        try:
            stripped = value.strip()
            if self.allow_float_strings:
                return Ok(int(float(stripped)))
            return Ok(int(stripped))
        except ValueError as e:
            return Err(AppError(
                code=ErrorCode.E2002_INVALID_FORMAT,
                message=f"Cannot coerce '{value}' to int: {e}",
                metadata={"value": value, "target": "int"},
            ))


@dataclass(frozen=True, slots=True)
class StringToFloat(CoercionRule[str, float]):
    """Coerce string to float."""
    
    @property
    def source_types(self) -> tuple[type, ...]:
        return (str,)
    
    @property
    def target_type(self) -> type[float]:
        return float
    
    def can_coerce(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        try:
            float(value.strip())
            return True
        except ValueError:
            return False
    
    def coerce(self, value: Any) -> Result[float, AppError]:
        if not isinstance(value, str):
            return Err(AppError(
                code=ErrorCode.E2004_INVALID_TYPE,
                message=f"Cannot coerce {type(value).__name__} to float",
            ))
        
        try:
            return Ok(float(value.strip()))
        except ValueError as e:
            return Err(AppError(
                code=ErrorCode.E2002_INVALID_FORMAT,
                message=f"Cannot coerce '{value}' to float: {e}",
            ))


@dataclass(frozen=True, slots=True)
class StringToDecimal(CoercionRule[str, Decimal]):
    """Coerce string to Decimal with precision preservation."""
    
    @property
    def source_types(self) -> tuple[type, ...]:
        return (str, int, float)
    
    @property
    def target_type(self) -> type[Decimal]:
        return Decimal
    
    def can_coerce(self, value: Any) -> bool:
        if isinstance(value, (int, float)):
            return True
        if isinstance(value, str):
            try:
                Decimal(value.strip())
                return True
            except InvalidOperation:
                return False
        return False
    
    def coerce(self, value: Any) -> Result[Decimal, AppError]:
        try:
            if isinstance(value, str):
                return Ok(Decimal(value.strip()))
            if isinstance(value, (int, float)):
                return Ok(Decimal(str(value)))
            return Err(AppError(
                code=ErrorCode.E2004_INVALID_TYPE,
                message=f"Cannot coerce {type(value).__name__} to Decimal",
            ))
        except InvalidOperation as e:
            return Err(AppError(
                code=ErrorCode.E2002_INVALID_FORMAT,
                message=f"Cannot coerce '{value}' to Decimal: {e}",
            ))


@dataclass(frozen=True, slots=True)
class StringToBool(CoercionRule[str, bool]):
    """Coerce string to boolean.
    
    Truthy: "true", "1", "yes", "on", "y"
    Falsy: "false", "0", "no", "off", "n"
    """
    true_values: frozenset[str] = frozenset({"true", "1", "yes", "on", "y"})
    false_values: frozenset[str] = frozenset({"false", "0", "no", "off", "n"})
    
    @property
    def source_types(self) -> tuple[type, ...]:
        return (str,)
    
    @property
    def target_type(self) -> type[bool]:
        return bool
    
    def can_coerce(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        lower = value.strip().lower()
        return lower in self.true_values or lower in self.false_values
    
    def coerce(self, value: Any) -> Result[bool, AppError]:
        if not isinstance(value, str):
            return Err(AppError(
                code=ErrorCode.E2004_INVALID_TYPE,
                message=f"Cannot coerce {type(value).__name__} to bool",
            ))
        
        lower = value.strip().lower()
        if lower in self.true_values:
            return Ok(True)
        if lower in self.false_values:
            return Ok(False)
        
        return Err(AppError(
            code=ErrorCode.E2002_INVALID_FORMAT,
            message=f"Cannot coerce '{value}' to bool. Valid values: {sorted(self.true_values | self.false_values)}",
        ))


@dataclass(frozen=True, slots=True)
class ISO8601ToDateTime(CoercionRule[str, datetime]):
    """Coerce ISO8601 string to datetime."""
    default_timezone: timezone | None = None
    
    @property
    def source_types(self) -> tuple[type, ...]:
        return (str,)
    
    @property
    def target_type(self) -> type[datetime]:
        return datetime
    
    def can_coerce(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        try:
            self._parse(value)
            return True
        except (ValueError, AttributeError):
            return False
    
    def _parse(self, value: str) -> datetime:
        """Parse ISO8601 string handling Z suffix."""
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None and self.default_timezone:
            dt = dt.replace(tzinfo=self.default_timezone)
        return dt
    
    def coerce(self, value: Any) -> Result[datetime, AppError]:
        if not isinstance(value, str):
            return Err(AppError(
                code=ErrorCode.E2004_INVALID_TYPE,
                message=f"Cannot coerce {type(value).__name__} to datetime",
            ))
        
        try:
            return Ok(self._parse(value))
        except (ValueError, AttributeError) as e:
            return Err(AppError(
                code=ErrorCode.E2012_INVALID_DATE,
                message=f"Cannot coerce '{value}' to datetime: {e}",
                metadata={"value": value, "target": "datetime", "format": "ISO8601"},
            ))


@dataclass(frozen=True, slots=True)
class ISO8601ToDate(CoercionRule[str, date]):
    """Coerce ISO8601 string to date."""
    
    @property
    def source_types(self) -> tuple[type, ...]:
        return (str,)
    
    @property
    def target_type(self) -> type[date]:
        return date
    
    def can_coerce(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        try:
            date.fromisoformat(value.strip())
            return True
        except ValueError:
            return False
    
    def coerce(self, value: Any) -> Result[date, AppError]:
        if not isinstance(value, str):
            return Err(AppError(
                code=ErrorCode.E2004_INVALID_TYPE,
                message=f"Cannot coerce {type(value).__name__} to date",
            ))
        
        try:
            return Ok(date.fromisoformat(value.strip()))
        except ValueError as e:
            return Err(AppError(
                code=ErrorCode.E2012_INVALID_DATE,
                message=f"Cannot coerce '{value}' to date: {e}",
            ))


@dataclass(frozen=True, slots=True)
class ISO8601ToTime(CoercionRule[str, time]):
    """Coerce ISO8601 string to time."""
    
    @property
    def source_types(self) -> tuple[type, ...]:
        return (str,)
    
    @property
    def target_type(self) -> type[time]:
        return time
    
    def can_coerce(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        try:
            time.fromisoformat(value.strip())
            return True
        except ValueError:
            return False
    
    def coerce(self, value: Any) -> Result[time, AppError]:
        if not isinstance(value, str):
            return Err(AppError(
                code=ErrorCode.E2004_INVALID_TYPE,
                message=f"Cannot coerce {type(value).__name__} to time",
            ))
        
        try:
            return Ok(time.fromisoformat(value.strip()))
        except ValueError as e:
            return Err(AppError(
                code=ErrorCode.E2002_INVALID_FORMAT,
                message=f"Cannot coerce '{value}' to time: {e}",
            ))


@dataclass(frozen=True, slots=True)
class DurationToTimedelta(CoercionRule[str, timedelta]):
    """Coerce duration string to timedelta.
    
    Supports formats:
    - ISO8601: "P1DT2H30M" (1 day, 2 hours, 30 minutes)
    - Simple: "1d", "2h", "30m", "45s"
    - Combined: "1d2h30m"
    """
    
    UNIT_MAP = {
        "d": "days", "day": "days", "days": "days",
        "h": "hours", "hr": "hours", "hour": "hours", "hours": "hours",
        "m": "minutes", "min": "minutes", "minute": "minutes", "minutes": "minutes",
        "s": "seconds", "sec": "seconds", "second": "seconds", "seconds": "seconds",
        "ms": "milliseconds", "millisecond": "milliseconds", "milliseconds": "milliseconds",
    }
    
    @property
    def source_types(self) -> tuple[type, ...]:
        return (str, int, float)
    
    @property
    def target_type(self) -> type[timedelta]:
        return timedelta
    
    def can_coerce(self, value: Any) -> bool:
        if isinstance(value, (int, float)):
            return True
        if isinstance(value, str):
            try:
                self._parse(value)
                return True
            except ValueError:
                return False
        return False
    
    def _parse(self, value: str) -> timedelta:
        """Parse duration string."""
        value = value.strip().lower()
        
        # ISO8601 duration
        if value.startswith("p"):
            return self._parse_iso8601(value)
        
        # Simple format: number followed by unit(s)
        pattern = r"(\d+\.?\d*)\s*([a-z]+)"
        matches = re.findall(pattern, value)
        
        if not matches:
            raise ValueError(f"Invalid duration format: {value}")
        
        kwargs: dict[str, float] = {}
        for num_str, unit in matches:
            unit_key = self.UNIT_MAP.get(unit)
            if not unit_key:
                raise ValueError(f"Unknown duration unit: {unit}")
            kwargs[unit_key] = kwargs.get(unit_key, 0) + float(num_str)
        
        return timedelta(**kwargs)
    
    def _parse_iso8601(self, value: str) -> timedelta:
        """Parse ISO8601 duration (P1DT2H30M)."""
        # Simplified parser for common cases
        pattern = r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?"
        match = re.match(pattern, value.upper())
        if not match:
            raise ValueError(f"Invalid ISO8601 duration: {value}")
        
        days = int(match.group(1) or 0)
        hours = int(match.group(2) or 0)
        minutes = int(match.group(3) or 0)
        seconds = int(match.group(4) or 0)
        
        return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
    
    def coerce(self, value: Any) -> Result[timedelta, AppError]:
        try:
            if isinstance(value, (int, float)):
                return Ok(timedelta(seconds=value))
            if isinstance(value, str):
                return Ok(self._parse(value))
            return Err(AppError(
                code=ErrorCode.E2004_INVALID_TYPE,
                message=f"Cannot coerce {type(value).__name__} to timedelta",
            ))
        except ValueError as e:
            return Err(AppError(
                code=ErrorCode.E2002_INVALID_FORMAT,
                message=f"Cannot coerce '{value}' to timedelta: {e}",
            ))


@dataclass(frozen=True, slots=True)
class StringToUUID(CoercionRule[str, UUID]):
    """Coerce string to UUID."""
    
    @property
    def source_types(self) -> tuple[type, ...]:
        return (str,)
    
    @property
    def target_type(self) -> type[UUID]:
        return UUID
    
    def can_coerce(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        try:
            UUID(value.strip())
            return True
        except ValueError:
            return False
    
    def coerce(self, value: Any) -> Result[UUID, AppError]:
        if not isinstance(value, str):
            return Err(AppError(
                code=ErrorCode.E2004_INVALID_TYPE,
                message=f"Cannot coerce {type(value).__name__} to UUID",
            ))
        
        try:
            return Ok(UUID(value.strip()))
        except ValueError as e:
            return Err(AppError(
                code=ErrorCode.E2011_INVALID_UUID,
                message=f"Cannot coerce '{value}' to UUID: {e}",
            ))


@dataclass(frozen=True, slots=True)
class StringToEnum(CoercionRule[str, Enum]):
    """Coerce string to Enum by name or value."""
    enum_class: type[Enum]
    by_value: bool = True
    case_insensitive: bool = True
    
    @property
    def source_types(self) -> tuple[type, ...]:
        return (str,)
    
    @property
    def target_type(self) -> type[Enum]:
        return self.enum_class
    
    def can_coerce(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        try:
            self._find_member(value)
            return True
        except ValueError:
            return False
    
    def _find_member(self, value: str) -> Enum:
        """Find enum member by name or value."""
        check_value = value.strip().upper() if self.case_insensitive else value.strip()
        
        # Try by name first
        for member in self.enum_class:
            name = member.name.upper() if self.case_insensitive else member.name
            if name == check_value:
                return member
        
        # Try by value
        if self.by_value:
            for member in self.enum_class:
                member_val = str(member.value)
                if self.case_insensitive:
                    member_val = member_val.upper()
                if member_val == check_value:
                    return member
        
        raise ValueError(f"No enum member matches: {value}")
    
    def coerce(self, value: Any) -> Result[Enum, AppError]:
        if not isinstance(value, str):
            return Err(AppError(
                code=ErrorCode.E2004_INVALID_TYPE,
                message=f"Cannot coerce {type(value).__name__} to {self.enum_class.__name__}",
            ))
        
        try:
            return Ok(self._find_member(value))
        except ValueError:
            valid = [m.name for m in self.enum_class]
            return Err(AppError(
                code=ErrorCode.E2002_INVALID_FORMAT,
                message=f"Cannot coerce '{value}' to {self.enum_class.__name__}. Valid: {valid}",
            ))


@dataclass(frozen=True, slots=True)
class ExplicitCoercion:
    """Coercion system with explicit opt-in rules.
    
    Usage:
        coercer = ExplicitCoercion()
        result = coercer.coerce("123", int)  # Ok(123)
        result = coercer.coerce("invalid", int)  # Err(AppError)
    """
    rules: tuple[CoercionRule, ...] = field(default_factory=lambda: (
        StringToInt(),
        StringToFloat(),
        StringToDecimal(),
        StringToBool(),
        ISO8601ToDateTime(),
        ISO8601ToDate(),
        ISO8601ToTime(),
        DurationToTimedelta(),
        StringToUUID(),
    ))
    
    def add_rule(self, rule: CoercionRule) -> ExplicitCoercion:
        """Add a coercion rule, returning new instance."""
        return ExplicitCoercion(rules=(*self.rules, rule))
    
    def coerce(self, value: Any, target_type: type[T]) -> Result[T, AppError]:
        """Attempt to coerce value to target type."""
        # If already correct type, return as-is
        if isinstance(value, target_type):
            return Ok(value)
        
        # Try each rule
        for rule in self.rules:
            if rule.target_type == target_type and rule.can_coerce(value):
                result = rule.coerce(value)
                if result.is_ok():
                    return result
        
        return Err(AppError(
            code=ErrorCode.E2004_INVALID_TYPE,
            message=f"Cannot coerce {type(value).__name__} to {target_type.__name__}",
            metadata={"source_type": type(value).__name__, "target_type": target_type.__name__},
        ))
    
    def coerce_or_none(self, value: Any, target_type: type[T]) -> T | None:
        """Coerce value or return None on failure."""
        result = self.coerce(value, target_type)
        return result.unwrap() if result.is_ok() else None


# Default coercion instance
DEFAULT_COERCER = ExplicitCoercion()


def coerce(value: Any, target_type: type[T]) -> Result[T, AppError]:
    """Convenience function using default coercer."""
    return DEFAULT_COERCER.coerce(value, target_type)


def coerce_or_none(value: Any, target_type: type[T]) -> T | None:
    """Convenience function for coerce-or-none pattern."""
    return DEFAULT_COERCER.coerce_or_none(value, target_type)


# ============================================================================
# Pydantic Integration - Annotated Types with Coercion
# ============================================================================

def _make_coercing_validator(target: type[T], coercer: ExplicitCoercion = DEFAULT_COERCER):
    """Create a BeforeValidator that coerces values."""
    def validate(v: Any) -> T:
        if isinstance(v, target):
            return v
        result = coercer.coerce(v, target)
        if result.is_err():
            raise ValueError(result.unwrap_err().message)
        return result.unwrap()
    return validate


# Pre-built coercing types for use with Annotated
CoercedInt = Annotated[int, BeforeValidator(_make_coercing_validator(int))]
CoercedFloat = Annotated[float, BeforeValidator(_make_coercing_validator(float))]
CoercedDecimal = Annotated[Decimal, BeforeValidator(_make_coercing_validator(Decimal))]
CoercedBool = Annotated[bool, BeforeValidator(_make_coercing_validator(bool))]
CoercedDateTime = Annotated[datetime, BeforeValidator(_make_coercing_validator(datetime))]
CoercedDate = Annotated[date, BeforeValidator(_make_coercing_validator(date))]
CoercedTime = Annotated[time, BeforeValidator(_make_coercing_validator(time))]
CoercedTimedelta = Annotated[timedelta, BeforeValidator(_make_coercing_validator(timedelta))]
CoercedUUID = Annotated[UUID, BeforeValidator(_make_coercing_validator(UUID))]
