"""Declarative Validation System

Schemas are the single source of truth for types, validation rules,
serialization, and documentation. Validation occurs at system boundaries
with parse-don't-validate semantics.

Key Features:
- BaseSchema with parse-don't-validate semantics
- Compositional validators (AND/OR/NOT combinators)
- Annotated type validators for declarative constraints
- Explicit opt-in coercion
- Structured error accumulation (fail-fast or collect-all)
- Schema generators for TypeScript, OpenAPI, JSON Schema, DB hints
- Boundary validators for API ingress, database egress, external services

Usage:
    from core.validation import (
        BaseSchema, Field, ValidationMode,
        StringLength, NumericRange, EmailValidator,
        Email, NonEmptyStr, PositiveInt,
        ValidationError, ValidationContext,
        parse_ingress, parse_db_egress,
        TypeScriptGenerator, generate_all,
    )
    
    class UserCreate(BaseSchema):
        email: Email
        username: NonEmptyStr
        age: PositiveInt
    
    # At API boundary
    result = parse_ingress(UserCreate, request.json())
    if result.is_err():
        return error_response(result.unwrap_err())
    user = result.unwrap()
"""

# Core schema system
from .schema import (
    BaseSchema,
    RequestSchema,
    ResponseSchema,
    EntitySchema,
    Field,
    ValidationMode,
    ValidationConfig,
    SensitiveStr,
    NonEmptyStr,
    SlugStr,
    PositiveInt,
    NonNegativeInt,
    PositiveFloat,
    Percentage,
    Rating,
    LanguageCode,
)

# Compositional validators
from .validators import (
    ValidationResult,
    AtomicValidator,
    # String validators
    StringLength,
    NonEmpty,
    RegexPattern,
    OneOf,
    # Numeric validators
    NumericRange,
    MultipleOf,
    Positive,
    NonNegative,
    # Format validators
    EmailValidator,
    UUIDValidator,
    DateTimeValidator,
    URLValidator,
    IPAddressValidator,
    # Collection validators
    ListLength,
    UniqueItems,
    # Combinators
    And,
    Or,
    Not,
    WithMessage,
    AllOf,
    AnyOf,
    # Custom validator
    CustomValidator,
    custom,
)

# Annotated type validators
from .annotated import (
    # String transformers
    Trimmed,
    LowerCase,
    UpperCase,
    TitleCase,
    NormalizedWhitespace,
    SafeString,
    # String validators
    NonEmpty as NonEmptyValidator,
    AsciiOnly,
    AlphaNumeric,
    SlugFormat,
    EmailFormat,
    UUIDFormat,
    # Length validators
    MinLen,
    MaxLen,
    Pattern,
    # Numeric validators
    Gt,
    Ge,
    Lt,
    Le,
    MultipleOf as MultipleOfValidator,
    Positive as PositiveValidator,
    NonNegative as NonNegativeValidator,
    PercentageRange,
    RatingRange,
    # DateTime validators
    PastDateTime,
    FutureDateTime,
    TimezoneAware,
    # Collection validators
    MinItems,
    MaxItems,
    UniqueItems as UniqueItemsValidator,
    # Pre-built types
    TrimmedStr,
    NonEmptyStr as NonEmptyStrAnnotated,
    Email,
    Slug,
    Username,
    PositiveInt as PositiveIntAnnotated,
    NonNegativeInt as NonNegativeIntAnnotated,
    PositiveFloat as PositiveFloatAnnotated,
    NonNegativeFloat,
    Percentage as PercentageAnnotated,
    Rating as RatingAnnotated,
    PastDatetime,
    FutureDatetime,
    TzAwareDatetime,
    LanguageCode as LanguageCodeAnnotated,
    # Decorator
    validator,
)

# Validation errors
from .errors import (
    ValidationError,
    ValidationErrorDetail,
    ValidationErrorAccumulator,
    FailFastAccumulator,
    CollectAllAccumulator,
    create_accumulator,
    ValidationContext,
)

# Coercion
from .coercion import (
    CoercionRule,
    StringToInt,
    StringToFloat,
    StringToDecimal,
    StringToBool,
    ISO8601ToDateTime,
    ISO8601ToDate,
    ISO8601ToTime,
    DurationToTimedelta,
    StringToUUID,
    StringToEnum,
    ExplicitCoercion,
    DEFAULT_COERCER,
    coerce,
    coerce_or_none,
    # Coercing types
    CoercedInt,
    CoercedFloat,
    CoercedDecimal,
    CoercedBool,
    CoercedDateTime,
    CoercedDate,
    CoercedTime,
    CoercedTimedelta,
    CoercedUUID,
)

# Schema generators
from .generators import (
    SchemaGenerator,
    TypeScriptGenerator,
    OpenAPIGenerator,
    JSONSchemaGenerator,
    DatabaseHintGenerator,
    DatabaseColumn,
    DatabaseTable,
    generate_all,
)

# Boundary validators
from .boundaries import (
    BoundaryValidator,
    validate_request,
    validate_response,
    validate_external,
    parse_ingress,
    parse_db_egress,
    parse_external,
    parse_batch,
    ValidatedBody,
    validated_body,
    ValidationBoundary,
)

__all__ = [
    # Core schema
    "BaseSchema",
    "RequestSchema",
    "ResponseSchema",
    "EntitySchema",
    "Field",
    "ValidationMode",
    "ValidationConfig",
    "SensitiveStr",
    "NonEmptyStr",
    "SlugStr",
    "PositiveInt",
    "NonNegativeInt",
    "PositiveFloat",
    "Percentage",
    "Rating",
    "LanguageCode",
    # Compositional validators
    "ValidationResult",
    "AtomicValidator",
    "StringLength",
    "NonEmpty",
    "RegexPattern",
    "OneOf",
    "NumericRange",
    "MultipleOf",
    "Positive",
    "NonNegative",
    "EmailValidator",
    "UUIDValidator",
    "DateTimeValidator",
    "URLValidator",
    "IPAddressValidator",
    "ListLength",
    "UniqueItems",
    "And",
    "Or",
    "Not",
    "WithMessage",
    "AllOf",
    "AnyOf",
    "CustomValidator",
    "custom",
    # Annotated validators
    "Trimmed",
    "LowerCase",
    "UpperCase",
    "TitleCase",
    "NormalizedWhitespace",
    "SafeString",
    "NonEmptyValidator",
    "AsciiOnly",
    "AlphaNumeric",
    "SlugFormat",
    "EmailFormat",
    "UUIDFormat",
    "MinLen",
    "MaxLen",
    "Pattern",
    "Gt",
    "Ge",
    "Lt",
    "Le",
    "MultipleOfValidator",
    "PositiveValidator",
    "NonNegativeValidator",
    "PercentageRange",
    "RatingRange",
    "PastDateTime",
    "FutureDateTime",
    "TimezoneAware",
    "MinItems",
    "MaxItems",
    "UniqueItemsValidator",
    "TrimmedStr",
    "NonEmptyStrAnnotated",
    "Email",
    "Slug",
    "Username",
    "PositiveIntAnnotated",
    "NonNegativeIntAnnotated",
    "PositiveFloatAnnotated",
    "NonNegativeFloat",
    "PercentageAnnotated",
    "RatingAnnotated",
    "PastDatetime",
    "FutureDatetime",
    "TzAwareDatetime",
    "LanguageCodeAnnotated",
    "validator",
    # Errors
    "ValidationError",
    "ValidationErrorDetail",
    "ValidationErrorAccumulator",
    "FailFastAccumulator",
    "CollectAllAccumulator",
    "create_accumulator",
    "ValidationContext",
    # Coercion
    "CoercionRule",
    "StringToInt",
    "StringToFloat",
    "StringToDecimal",
    "StringToBool",
    "ISO8601ToDateTime",
    "ISO8601ToDate",
    "ISO8601ToTime",
    "DurationToTimedelta",
    "StringToUUID",
    "StringToEnum",
    "ExplicitCoercion",
    "DEFAULT_COERCER",
    "coerce",
    "coerce_or_none",
    "CoercedInt",
    "CoercedFloat",
    "CoercedDecimal",
    "CoercedBool",
    "CoercedDateTime",
    "CoercedDate",
    "CoercedTime",
    "CoercedTimedelta",
    "CoercedUUID",
    # Generators
    "SchemaGenerator",
    "TypeScriptGenerator",
    "OpenAPIGenerator",
    "JSONSchemaGenerator",
    "DatabaseHintGenerator",
    "DatabaseColumn",
    "DatabaseTable",
    "generate_all",
    # Boundaries
    "BoundaryValidator",
    "validate_request",
    "validate_response",
    "validate_external",
    "parse_ingress",
    "parse_db_egress",
    "parse_external",
    "parse_batch",
    "ValidatedBody",
    "validated_body",
    "ValidationBoundary",
]
