"""Core Schema System with Pydantic v2 Modern Features

Schemas are the single source of truth for types, validation rules,
serialization, and documentation. Parse-don't-validate semantics ensure
invalid data is unrepresentable in domain types.

Key Features:
- Discriminated unions for polymorphic types
- Functional validators with @field_validator and @model_validator
- Computed fields with caching
- Strict mode by default
- Rich JSON Schema generation with x-* extensions
"""
from __future__ import annotations

from enum import Enum
from typing import (
    Annotated, Any, Callable, ClassVar, Generic, Literal,
    Self, TypeVar, get_args, get_origin,
)
from dataclasses import dataclass, field as dataclass_field
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from uuid import UUID as StdUUID
import re

from pydantic import (
    BaseModel as PydanticBaseModel,
    Field as PydanticField,
    field_validator,
    field_serializer,
    model_validator,
    ConfigDict,
    ValidationInfo,
    computed_field,
    BeforeValidator,
    AfterValidator,
    PlainSerializer,
    WrapValidator,
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
)
from pydantic.functional_validators import WrapValidator
from pydantic_core import CoreSchema, core_schema
from pydantic.json_schema import JsonSchemaValue

from core.errors import AppError, ErrorCode

T = TypeVar("T")


class ValidationMode(str, Enum):
    """Validation accumulation strategy."""
    FAIL_FAST = "fail_fast"
    COLLECT_ALL = "collect_all"


@dataclass(frozen=True, slots=True)
class ValidationConfig:
    """Configuration for schema validation."""
    mode: ValidationMode = ValidationMode.FAIL_FAST
    enable_coercion: bool = False
    strict_types: bool = True
    redact_sensitive: bool = True
    max_errors: int = 50
    locale: str = "en"


class SensitiveStr(str):
    """Marker type for sensitive string values that should be redacted in errors."""
    
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.str_schema(),
        )
    
    @classmethod
    def _validate(cls, v: str) -> SensitiveStr:
        return cls(v)
    
    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return {"type": "string", "x-sensitive": True, "writeOnly": True}


class NonEmptyStr(str):
    """Non-empty string with automatic trimming."""
    
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.str_schema(min_length=1, strip_whitespace=True),
        )
    
    @classmethod
    def _validate(cls, v: str) -> NonEmptyStr:
        if not (stripped := v.strip()): raise ValueError("String cannot be empty or whitespace-only")
        return cls(stripped)


class SlugStr(str):
    """URL-safe slug string: lowercase alphanumeric with hyphens."""
    PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.str_schema(min_length=1, max_length=100),
        )
    
    @classmethod
    def _validate(cls, v: str) -> SlugStr:
        if not cls.PATTERN.match(normalized := v.lower().strip()):
            raise ValueError(f"Invalid slug format: must be lowercase alphanumeric with hyphens, got '{v}'")
        return cls(normalized)
    
    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return {
            "type": "string",
            "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$",
            "minLength": 1,
            "maxLength": 100,
            "x-slug": True,
        }


def Field(
    default: Any = ...,
    *,
    description: str | None = None,
    examples: list[Any] | None = None,
    title: str | None = None,
    # Validation constraints
    min_length: int | None = None,
    max_length: int | None = None,
    pattern: str | None = None,
    gt: float | None = None,
    ge: float | None = None,
    lt: float | None = None,
    le: float | None = None,
    multiple_of: float | None = None,
    # Schema extensions
    sensitive: bool = False,
    deprecated: bool = False,
    db_column: str | None = None,
    db_type: str | None = None,
    db_index: bool = False,
    db_unique: bool = False,
    suggested_fix_template: str | None = None,
    **kwargs,
) -> Any:
    """Extended Field with validation metadata and schema extensions.
    
    Args:
        default: Default value or ... for required
        description: Human-readable field description
        examples: Example values for documentation
        title: Field title for schemas
        min_length: Minimum string length
        max_length: Maximum string length  
        pattern: Regex pattern for string validation
        gt: Greater than (exclusive minimum)
        ge: Greater than or equal (inclusive minimum)
        lt: Less than (exclusive maximum)
        le: Less than or equal (inclusive maximum)
        multiple_of: Value must be multiple of this
        sensitive: Mark field as sensitive (redact in errors)
        deprecated: Mark field as deprecated
        db_column: Database column name override
        db_type: Database type hint (VARCHAR, TEXT, JSONB, etc.)
        db_index: Generate database index
        db_unique: Generate unique constraint
        suggested_fix_template: Template for error suggested_fix generation
    """
    pydantic_kwargs: dict[str, Any] = {"default": default}
    
    if description:
        pydantic_kwargs["description"] = description
    if examples:
        pydantic_kwargs["examples"] = examples
    if title:
        pydantic_kwargs["title"] = title
    
    # Numeric constraints
    if gt is not None:
        pydantic_kwargs["gt"] = gt
    if ge is not None:
        pydantic_kwargs["ge"] = ge
    if lt is not None:
        pydantic_kwargs["lt"] = lt
    if le is not None:
        pydantic_kwargs["le"] = le
    if multiple_of is not None:
        pydantic_kwargs["multiple_of"] = multiple_of
    
    # String constraints
    if min_length is not None:
        pydantic_kwargs["min_length"] = min_length
    if max_length is not None:
        pydantic_kwargs["max_length"] = max_length
    if pattern is not None:
        pydantic_kwargs["pattern"] = pattern
    
    # Build JSON schema extensions
    schema_extra: dict[str, Any] = {}
    if sensitive:
        schema_extra["x-sensitive"] = True
    if deprecated:
        schema_extra["deprecated"] = True
    if db_column:
        schema_extra["x-db-column"] = db_column
    if db_type:
        schema_extra["x-db-type"] = db_type
    if db_index:
        schema_extra["x-db-index"] = True
    if db_unique:
        schema_extra["x-db-unique"] = True
    if suggested_fix_template:
        schema_extra["x-suggested-fix"] = suggested_fix_template
    
    if schema_extra:
        pydantic_kwargs["json_schema_extra"] = schema_extra
    
    pydantic_kwargs.update(kwargs)
    return PydanticField(**pydantic_kwargs)


class BaseSchema(PydanticBaseModel):
    """Base schema with parse-don't-validate semantics.
    
    Invalid data is unrepresentable in domain types. All validation
    happens at construction time, making instances immutable proofs
    of validity.
    
    Features:
    - Strict type validation by default
    - Rich error messages with JSON paths
    - Schema generation for TypeScript, OpenAPI, JSON Schema
    - Database migration hints via x-db-* extensions
    """
    
    model_config = ConfigDict(
        # Strict validation
        strict=True,
        validate_assignment=True,
        validate_default=True,
        revalidate_instances="always",
        # Naming
        populate_by_name=True,
        use_enum_values=False,
        # Serialization
        ser_json_timedelta="iso8601",
        ser_json_bytes="base64",
        from_attributes=True,
        # JSON Schema
        json_schema_mode="validation",
        json_schema_serialization_defaults_required=True,
        # Extra fields handling
        extra="forbid",
    )
    
    # Class-level configuration for validation behavior
    _validation_config: ClassVar[ValidationConfig] = ValidationConfig()
    _sensitive_fields: ClassVar[frozenset[str]] = frozenset()
    
    def __init_subclass__(cls, **kwargs):
        """Collect sensitive fields from annotations."""
        super().__init_subclass__(**kwargs)
        sensitive = {name for name, field_info in cls.model_fields.items() if (
            field_info.json_schema_extra and isinstance(field_info.json_schema_extra, dict) and
            field_info.json_schema_extra.get("x-sensitive")) or
            field_info.annotation is SensitiveStr or
            (get_origin(field_info.annotation) and SensitiveStr in get_args(field_info.annotation))}
        cls._sensitive_fields = frozenset(sensitive)
    
    @classmethod
    def parse(cls, data: dict[str, Any] | Any, *, strict: bool = True) -> Self:
        """Parse data into validated schema instance.
        
        Raises ValidationError if data is invalid.
        Uses parse-don't-validate: invalid data cannot be represented.
        """
        try:
            return cls.model_validate(data, strict=strict)
        except Exception as e:
            from .errors import ValidationError, ValidationErrorDetail
            
            if isinstance(e, ValidationError):
                raise
            
            # Convert Pydantic errors to our ValidationError
            if hasattr(e, "errors"):
                details = [
                    ValidationErrorDetail(
                        field_path=".".join(str(loc) for loc in err.get("loc", [])),
                        constraint=err.get("type", "validation_error"),
                        actual_value=cls._maybe_redact(
                            ".".join(str(loc) for loc in err.get("loc", [])),
                            err.get("input"),
                        ),
                        message=err.get("msg", "Validation failed"),
                        suggested_fix=cls._suggest_fix(err),
                    )
                    for err in e.errors()
                ]
                raise ValidationError(
                    message="Validation failed",
                    details=details,
                    mode=cls._validation_config.mode,
                    sensitive_fields=cls._sensitive_fields,
                ) from e
            
            raise ValidationError(
                message=str(e),
                details=[],
                mode=cls._validation_config.mode,
            ) from e
    
    @classmethod
    def parse_lax(cls, data: dict[str, Any] | Any) -> Self:
        return cls.parse(data, strict=False)
    
    @classmethod
    def parse_result(cls, data: dict[str, Any] | Any, *, strict: bool = True):
        """Parse data returning Result type for monadic error handling."""
        from core.errors import Ok, Err
        from .errors import ValidationError
        try: return Ok(cls.parse(data, strict=strict))
        except ValidationError as e: return Err(e)
    
    @classmethod
    def _maybe_redact(cls, field_path: str, value: Any) -> Any:
        """Redact sensitive field values."""
        field_name = field_path.split(".")[-1] if "." in field_path else field_path
        return "[REDACTED]" if field_name in cls._sensitive_fields else value
    
    @classmethod
    def _suggest_fix(cls, error: dict[str, Any]) -> str | None:
        """Generate suggested fix from error context."""
        err_type = error.get("type", "")
        ctx = error.get("ctx", {})
        
        suggestions = {
            "string_too_short": lambda: f"Value must be at least {ctx.get('min_length', '?')} characters",
            "string_too_long": lambda: f"Truncate to {ctx.get('max_length', '?')} characters or less",
            "string_pattern_mismatch": lambda: f"Value must match pattern: {ctx.get('pattern', '?')}",
            "greater_than": lambda: f"Use a value greater than {ctx.get('gt', '?')}",
            "greater_than_equal": lambda: f"Use a value of {ctx.get('ge', '?')} or more",
            "less_than": lambda: f"Use a value less than {ctx.get('lt', '?')}",
            "less_than_equal": lambda: f"Use a value of {ctx.get('le', '?')} or less",
            "missing": lambda: "This field is required",
            "enum": lambda: f"Valid options: {', '.join(str(v) for v in ctx.get('expected', []))}",
            "uuid_parsing": lambda: "Provide a valid UUID (e.g., '550e8400-e29b-41d4-a716-446655440000')",
            "datetime_parsing": lambda: "Provide ISO8601 datetime (e.g., '2024-01-15T10:30:00Z')",
            "date_parsing": lambda: "Provide ISO8601 date (e.g., '2024-01-15')",
            "int_parsing": lambda: "Provide a valid integer number",
            "float_parsing": lambda: "Provide a valid decimal number",
            "bool_parsing": lambda: "Provide true or false",
            "url_parsing": lambda: "Provide a valid URL (e.g., 'https://example.com')",
            "email_parsing": lambda: "Provide a valid email (e.g., 'user@example.com')",
        }
        
        if err_type in suggestions: return suggestions[err_type]()
        if (loc := error.get("loc", [])) and (field_info := cls.model_fields.get(str(loc[-1]))):
            if field_info.json_schema_extra and isinstance(extra := field_info.json_schema_extra, dict):
                return extra.get("x-suggested-fix")
        return None
    
    def to_dict(self, *, exclude_none: bool = False, exclude_unset: bool = False, by_alias: bool = False) -> dict[str, Any]:
        """Serialize to dictionary."""
        return self.model_dump(exclude_none=exclude_none, exclude_unset=exclude_unset, by_alias=by_alias)
    
    def to_json(self, *, exclude_none: bool = False, exclude_unset: bool = False,
                by_alias: bool = False, indent: int | None = None) -> str:
        """Serialize to JSON string."""
        return self.model_dump_json(exclude_none=exclude_none, exclude_unset=exclude_unset, by_alias=by_alias, indent=indent)
    
    @classmethod
    def json_schema(cls) -> dict[str, Any]: return cls.model_json_schema(mode="validation")
    
    @classmethod
    def openapi_schema(cls) -> dict[str, Any]: return cls.model_json_schema(mode="serialization")
    
    @computed_field
    @property
    def _schema_name(self) -> str: return self.__class__.__name__


class RequestSchema(BaseSchema):
    """Base schema for API request bodies.
    
    Enables stricter validation suitable for incoming data.
    """
    model_config = ConfigDict(
        **BaseSchema.model_config,
        str_strip_whitespace=True,
    )


class ResponseSchema(BaseSchema):
    """Base schema for API responses.
    
    Enables serialization-friendly settings.
    """
    model_config = ConfigDict(
        strict=True,
        validate_assignment=True,
        validate_default=True,
        revalidate_instances="always",
        populate_by_name=True,
        use_enum_values=False,
        ser_json_timedelta="iso8601",
        ser_json_bytes="base64",
        from_attributes=True,
        json_schema_mode="validation",
        json_schema_serialization_defaults_required=True,
        extra="ignore",
    )


class EntitySchema(BaseSchema):
    """Base schema for database entities.
    
    Includes common fields like id, created_at, updated_at.
    """
    id: StdUUID = Field(description="Unique identifier")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp",
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Last update timestamp",
    )


# Type aliases for common validated types
PositiveInt = Annotated[int, PydanticField(gt=0)]
NonNegativeInt = Annotated[int, PydanticField(ge=0)]
PositiveFloat = Annotated[float, PydanticField(gt=0.0)]
Percentage = Annotated[float, PydanticField(ge=0.0, le=100.0)]
Rating = Annotated[int, PydanticField(ge=0, le=5)]
LanguageCode = Annotated[str, PydanticField(min_length=2, max_length=10, pattern=r"^[a-z]{2,3}(-[A-Z]{2})?$")]
