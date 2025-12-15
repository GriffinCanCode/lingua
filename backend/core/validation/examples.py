"""Example Schemas Demonstrating Validation System

Shows usage of atomic validators, combinators, coercion, and metadata.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID
from typing import Optional

from .schema import BaseSchema, Field
from .validators import (
    StringLength,
    NumericRange,
    RegexPattern,
    EmailValidator,
    UUIDValidator,
    And,
    Or,
)


class UserCreateSchema(BaseSchema):
    """User creation schema with comprehensive validation."""
    
    email: str = Field(
        ...,
        description="User email address",
        validators=[EmailValidator()],
        min_length=5,
        max_length=255,
        sensitive=False,
        db_column="email",
        db_type="VARCHAR(255)",
        db_constraints=["UNIQUE", "NOT NULL"],
    )
    
    username: str = Field(
        ...,
        description="Unique username",
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_]+$",
        db_column="username",
        db_type="VARCHAR(50)",
        db_constraints=["UNIQUE", "NOT NULL"],
    )
    
    password: str = Field(
        ...,
        description="User password",
        min_length=8,
        max_length=128,
        sensitive=True,  # Will be redacted in errors
        validators=[
            And(
                StringLength(min_length=8, max_length=128),
                RegexPattern(pattern=r".*[A-Z].*"),  # At least one uppercase
                RegexPattern(pattern=r".*[a-z].*"),  # At least one lowercase
                RegexPattern(pattern=r".*[0-9].*"),  # At least one digit
            )
        ],
    )
    
    age: Optional[int] = Field(
        None,
        description="User age",
        ge=0,
        le=150,
        db_type="INTEGER",
    )
    
    target_language: str = Field(
        "ru",
        description="Target language code",
        min_length=2,
        max_length=10,
        db_type="VARCHAR(10)",
    )


class SentenceCreateSchema(BaseSchema):
    """Sentence creation with validation."""
    
    text: str = Field(
        ...,
        description="Sentence text",
        min_length=1,
        max_length=1000,
        db_column="text",
        db_type="TEXT",
        db_constraints=["NOT NULL"],
    )
    
    language: str = Field(
        "ru",
        description="Language code",
        min_length=2,
        max_length=10,
        db_type="VARCHAR(10)",
    )
    
    translation: Optional[str] = Field(
        None,
        description="Translation",
        max_length=1000,
        db_type="TEXT",
    )
    
    complexity_score: int = Field(
        1,
        description="Complexity score (1-10)",
        ge=1,
        le=10,
        db_type="INTEGER",
        db_constraints=["CHECK (complexity_score >= 1 AND complexity_score <= 10)"],
    )


class ReviewResultSchema(BaseSchema):
    """Review result with validation."""
    
    pattern_id: UUID = Field(
        ...,
        description="Pattern ID",
        validators=[UUIDValidator()],
        db_type="UUID",
        db_constraints=["NOT NULL", "REFERENCES syntactic_patterns(id)"],
    )
    
    quality: int = Field(
        ...,
        description="SM-2 quality rating (0-5)",
        ge=0,
        le=5,
        db_type="INTEGER",
        db_constraints=["CHECK (quality >= 0 AND quality <= 5)"],
    )


# Example of using combinators
class FlexibleInputSchema(BaseSchema):
    """Example showing OR combinator."""
    
    identifier: str = Field(
        ...,
        description="Either email or username",
        validators=[
            Or(
                EmailValidator(),
                And(
                    StringLength(min_length=3, max_length=50),
                    RegexPattern(pattern=r"^[a-zA-Z0-9_]+$"),
                ),
            )
        ],
    )

