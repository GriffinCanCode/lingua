"""Schema Generators

Generate TypeScript types, OpenAPI specs, JSON Schema, and database migration hints
from schema definitions. Schemas are the single source of truth.

Features:
- TypeScript interfaces with JSDoc comments
- OpenAPI 3.1 compatible schemas
- JSON Schema draft 2020-12
- Database migration hints with constraints
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Union, get_origin, get_args
from dataclasses import dataclass
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from uuid import UUID
from enum import Enum
import json
import re

from pydantic import BaseModel


class SchemaGenerator(ABC):
    """Base class for schema generators."""
    
    @abstractmethod
    def generate(self, schema: type[BaseModel]) -> str:
        """Generate schema representation."""
    
    def generate_all(self, *schemas: type[BaseModel], separator: str = "\n\n") -> str:
        return separator.join(self.generate(s) for s in schemas)


class TypeScriptGenerator(SchemaGenerator):
    """Generate TypeScript type definitions.
    
    Features:
    - Interfaces with proper optionality
    - JSDoc comments from field descriptions
    - Nested type support
    - Enum generation
    - Union types
    """
    
    TYPE_MAP: dict[type, str] = {
        str: "string",
        int: "number",
        float: "number",
        bool: "boolean",
        Decimal: "string",  # Use string for precision
        bytes: "string",  # Base64 encoded
        datetime: "string",  # ISO8601
        date: "string",  # ISO8601 date
        time: "string",  # ISO8601 time
        timedelta: "string",  # ISO8601 duration
        UUID: "string",  # UUID string
        dict: "Record<string, unknown>",
        list: "unknown[]",
        type(None): "null",
    }
    
    def __init__(self, export_style: str = "export", use_type_alias: bool = False):
        self.export_style, self.use_type_alias = export_style, use_type_alias
    
    def generate(self, schema: type[BaseModel]) -> str:
        """Generate TypeScript interface."""
        lines: list[str] = []
        
        # Add schema docstring as JSDoc
        if schema.__doc__:
            lines.append("/**")
            for line in schema.__doc__.strip().split("\n"):
                lines.append(f" * {line.strip()}")
            lines.append(" */")
        
        # Interface declaration
        keyword = "type" if self.use_type_alias else "interface"
        prefix = self.export_style
        eq = " =" if self.use_type_alias else ""
        lines.append(f"{prefix} {keyword} {schema.__name__}{eq} {{")
        
        # Fields
        for field_name, field_info in schema.model_fields.items():
            field_lines = self._generate_field(field_name, field_info)
            lines.extend(f"  {line}" for line in field_lines)
        
        lines.append("}")
        
        return "\n".join(lines)
    
    def _generate_field(self, name: str, field_info: Any) -> list[str]:
        """Generate TypeScript field definition with JSDoc."""
        lines: list[str] = []
        
        # JSDoc comment
        comments: list[str] = []
        if field_info.description:
            comments.append(field_info.description)
        
        # Check for deprecation
        if field_info.json_schema_extra and isinstance(field_info.json_schema_extra, dict):
            if field_info.json_schema_extra.get("deprecated"):
                comments.append("@deprecated")
            if field_info.json_schema_extra.get("x-sensitive"):
                comments.append("@sensitive This field contains sensitive data")
        
        if comments:
            if len(comments) == 1:
                lines.append(f"/** {comments[0]} */")
            else:
                lines.append("/**")
                for comment in comments:
                    lines.append(f" * {comment}")
                lines.append(" */")
        
        # Field definition
        ts_type = self._python_to_ts(field_info.annotation)
        optional = "?" if not field_info.is_required() else ""
        readonly = "readonly " if field_info.frozen else ""
        
        lines.append(f"{readonly}{name}{optional}: {ts_type};")
        
        return lines
    
    def _python_to_ts(self, python_type: Any) -> str:
        """Convert Python type to TypeScript type."""
        if python_type is None: return "null"
        
        origin, args = get_origin(python_type), get_args(python_type)
        
        if origin is Union:
            if not (non_none := [a for a in args if a is not type(None)]): return "null"
            types = [self._python_to_ts(t) for t in non_none]
            if type(None) in args: types.append("null")
            return " | ".join(types)
        
        if origin is list: return f"{self._python_to_ts(args[0])}[]" if args else "unknown[]"
        if origin is tuple: return f"[{', '.join(self._python_to_ts(t) for t in args)}]" if args else "unknown[]"
        if origin is dict:
            return (f"Record<{self._python_to_ts(args[0])}, {self._python_to_ts(args[1])}>"
                if args and len(args) == 2 else "Record<string, unknown>")
        if origin in (set, frozenset): return f"{self._python_to_ts(args[0])}[]" if args else "unknown[]"
        
        if hasattr(python_type, "__origin__") and str(python_type.__origin__) == "typing.Literal":
            return " | ".join(f'"{v}"' if isinstance(v, str) else str(v).lower() for v in args)
        if isinstance(python_type, type) and issubclass(python_type, Enum): return self._generate_enum_type(python_type)
        if python_type in self.TYPE_MAP: return self.TYPE_MAP[python_type]
        if isinstance(python_type, type) and issubclass(python_type, BaseModel): return python_type.__name__
        return "unknown"
    
    def _generate_enum_type(self, enum_class: type[Enum]) -> str:
        """Generate TypeScript enum or union type."""
        values = []
        for member in enum_class:
            if isinstance(member.value, str):
                values.append(f'"{member.value}"')
            elif isinstance(member.value, (int, float)):
                values.append(str(member.value))
            else:
                values.append(f'"{member.name}"')
        return " | ".join(values)
    
    def generate_enum(self, enum_class: type[Enum]) -> str:
        """Generate standalone TypeScript enum."""
        lines = [f"export enum {enum_class.__name__} {{"]
        for member in enum_class:
            if isinstance(member.value, str):
                lines.append(f'  {member.name} = "{member.value}",')
            else:
                lines.append(f"  {member.name} = {member.value},")
        lines.append("}")
        return "\n".join(lines)


class OpenAPIGenerator(SchemaGenerator):
    """Generate OpenAPI 3.1 compatible schemas."""
    
    def __init__(self, include_examples: bool = True): self.include_examples = include_examples
    
    def generate(self, schema: type[BaseModel]) -> str:
        """Generate OpenAPI schema JSON."""
        openapi_schema = schema.model_json_schema(mode="serialization")
        if schema.__doc__: openapi_schema["description"] = schema.__doc__.strip()
        return json.dumps(openapi_schema, indent=2)
    
    def generate_components(self, *schemas: type[BaseModel]) -> dict[str, Any]:
        """Generate OpenAPI components/schemas section."""
        components: dict[str, Any] = {"schemas": {}}
        
        for schema in schemas:
            schema_def = schema.model_json_schema(mode="serialization")
            
            # Extract definitions
            if "$defs" in schema_def:
                for name, definition in schema_def["$defs"].items():
                    if name not in components["schemas"]:
                        components["schemas"][name] = definition
                del schema_def["$defs"]
            
            components["schemas"][schema.__name__] = schema_def
        
        return components


class JSONSchemaGenerator(SchemaGenerator):
    """Generate JSON Schema (draft 2020-12)."""
    
    def __init__(self, mode: str = "validation"): self.mode = mode
    
    def generate(self, schema: type[BaseModel]) -> str:
        """Generate JSON Schema."""
        json_schema = schema.model_json_schema(mode=self.mode)
        json_schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        return json.dumps(json_schema, indent=2)


@dataclass
class DatabaseColumn:
    """Database column definition."""
    name: str
    db_type: str
    nullable: bool = True
    primary_key: bool = False
    unique: bool = False
    indexed: bool = False
    default: Any = None
    check_constraint: str | None = None
    foreign_key: str | None = None
    comment: str | None = None


@dataclass
class DatabaseTable:
    """Database table definition."""
    name: str
    columns: list[DatabaseColumn]
    indexes: list[dict[str, Any]] | None = None
    constraints: list[str] | None = None
    comment: str | None = None


class DatabaseHintGenerator(SchemaGenerator):
    """Generate database migration hints from schema.
    
    Interprets x-db-* JSON schema extensions:
    - x-db-column: Override column name
    - x-db-type: Override database type (VARCHAR, TEXT, JSONB, etc.)
    - x-db-index: Generate index on column
    - x-db-unique: Generate unique constraint
    """
    
    # Python type to database type mapping
    TYPE_MAP: dict[type, str] = {
        str: "VARCHAR(255)",
        int: "INTEGER",
        float: "DOUBLE PRECISION",
        bool: "BOOLEAN",
        bytes: "BYTEA",
        Decimal: "NUMERIC",
        datetime: "TIMESTAMP WITH TIME ZONE",
        date: "DATE",
        time: "TIME",
        timedelta: "INTERVAL",
        UUID: "UUID",
        dict: "JSONB",
        list: "JSONB",
    }
    
    def generate(self, schema: type[BaseModel]) -> str:
        """Generate database migration hints."""
        table = self._generate_table(schema)
        return json.dumps(self._table_to_dict(table), indent=2)
    
    def _generate_table(self, schema: type[BaseModel]) -> DatabaseTable:
        """Generate table definition from schema."""
        table_name = self._to_snake_case(schema.__name__)
        columns: list[DatabaseColumn] = []
        indexes: list[dict[str, Any]] = []
        
        for field_name, field_info in schema.model_fields.items():
            column = self._generate_column(field_name, field_info)
            columns.append(column)
            
            if column.indexed and not column.primary_key:
                indexes.append({
                    "name": f"ix_{table_name}_{column.name}",
                    "columns": [column.name],
                })
        
        return DatabaseTable(
            name=table_name,
            columns=columns,
            indexes=indexes if indexes else None,
            comment=schema.__doc__.strip() if schema.__doc__ else None,
        )
    
    def _generate_column(self, name: str, field_info: Any) -> DatabaseColumn:
        """Generate column definition from field info."""
        # Get base column name
        column_name = self._to_snake_case(name)
        
        # Get database type
        db_type = self._python_to_db_type(field_info.annotation)
        
        # Check for JSON schema extras
        extra = {}
        if field_info.json_schema_extra and isinstance(field_info.json_schema_extra, dict):
            extra = field_info.json_schema_extra
        
        # Override from extras
        if "x-db-column" in extra:
            column_name = extra["x-db-column"]
        if "x-db-type" in extra:
            db_type = extra["x-db-type"]
        
        # Handle string length constraints
        annotation = field_info.annotation
        if annotation is str or (get_origin(annotation) is Union and str in get_args(annotation)):
            # Check for max_length
            if hasattr(field_info, "metadata"):
                for meta in field_info.metadata:
                    if hasattr(meta, "max_length") and meta.max_length:
                        db_type = f"VARCHAR({meta.max_length})"
                        break
        
        return DatabaseColumn(
            name=column_name,
            db_type=db_type,
            nullable=not field_info.is_required(),
            primary_key=column_name == "id",
            unique=extra.get("x-db-unique", False),
            indexed=extra.get("x-db-index", False) or column_name == "id",
            default=field_info.default if field_info.default is not ... else None,
            comment=field_info.description,
        )
    
    def _python_to_db_type(self, python_type: Any) -> str:
        """Convert Python type to database type."""
        origin, args = get_origin(python_type), get_args(python_type)
        
        if origin is Union and (non_none := [a for a in args if a is not type(None)]):
            return self._python_to_db_type(non_none[0])
        if origin in (list, dict): return "JSONB"
        if isinstance(python_type, type) and issubclass(python_type, Enum): return "VARCHAR(50)"
        if python_type in self.TYPE_MAP: return self.TYPE_MAP[python_type]
        if isinstance(python_type, type) and issubclass(python_type, BaseModel): return "JSONB"
        return "TEXT"
    
    def _to_snake_case(self, name: str) -> str:
        """Convert CamelCase to snake_case."""
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)).lower()
    
    def _table_to_dict(self, table: DatabaseTable) -> dict[str, Any]:
        """Serialize table to dictionary."""
        return {
            "table_name": table.name,
            "columns": [
                {
                    "name": c.name,
                    "type": c.db_type,
                    "nullable": c.nullable,
                    "primary_key": c.primary_key,
                    "unique": c.unique,
                    "indexed": c.indexed,
                    "default": c.default if c.default is not None else None,
                    "comment": c.comment,
                }
                for c in table.columns
            ],
            "indexes": table.indexes or [],
            "comment": table.comment,
        }
    
    def generate_alembic_migration(self, schema: type[BaseModel]) -> str:
        """Generate Alembic migration code."""
        table = self._generate_table(schema)
        lines = [
            "from alembic import op",
            "import sqlalchemy as sa",
            "from sqlalchemy.dialects.postgresql import UUID, JSONB",
            "",
            "",
            "def upgrade():",
            f"    op.create_table(",
            f'        "{table.name}",',
        ]
        
        for col in table.columns:
            col_def = self._column_to_alembic(col)
            lines.append(f"        {col_def},")
        
        lines.append("    )")
        
        # Add indexes
        if table.indexes:
            for idx in table.indexes:
                cols = ", ".join(f'"{c}"' for c in idx["columns"])
                lines.append(f'    op.create_index("{idx["name"]}", "{table.name}", [{cols}])')
        
        lines.extend([
            "",
            "",
            "def downgrade():",
            f'    op.drop_table("{table.name}")',
        ])
        
        return "\n".join(lines)
    
    def _column_to_alembic(self, col: DatabaseColumn) -> str:
        """Convert column to Alembic column definition."""
        type_map = {
            "INTEGER": "sa.Integer()",
            "BIGINT": "sa.BigInteger()",
            "DOUBLE PRECISION": "sa.Float()",
            "BOOLEAN": "sa.Boolean()",
            "TEXT": "sa.Text()",
            "BYTEA": "sa.LargeBinary()",
            "NUMERIC": "sa.Numeric()",
            "DATE": "sa.Date()",
            "TIME": "sa.Time()",
            "INTERVAL": "sa.Interval()",
            "UUID": "UUID(as_uuid=True)",
            "JSONB": "JSONB()",
            "TIMESTAMP WITH TIME ZONE": "sa.DateTime(timezone=True)",
        }
        
        # Handle VARCHAR
        if col.db_type.startswith("VARCHAR"):
            match = re.match(r"VARCHAR\((\d+)\)", col.db_type)
            length = match.group(1) if match else "255"
            sa_type = f"sa.String({length})"
        else:
            sa_type = type_map.get(col.db_type, "sa.Text()")
        
        parts = [f'sa.Column("{col.name}", {sa_type}']
        
        if col.primary_key:
            parts.append("primary_key=True")
        if not col.nullable:
            parts.append("nullable=False")
        if col.unique:
            parts.append("unique=True")
        if col.indexed and not col.primary_key:
            parts.append("index=True")
        
        return ", ".join(parts) + ")"


def generate_all(
    schema: type[BaseModel],
    output_dir: str | None = None,
) -> dict[str, str]:
    """Generate all schema representations.
    
    Returns dict with keys: typescript, openapi, json_schema, db_hints
    """
    generators = {
        "typescript": TypeScriptGenerator(),
        "openapi": OpenAPIGenerator(),
        "json_schema": JSONSchemaGenerator(),
        "db_hints": DatabaseHintGenerator(),
    }
    
    results = {name: gen.generate(schema) for name, gen in generators.items()}
    
    if output_dir:
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        extensions = {
            "typescript": ".ts",
            "openapi": ".openapi.json",
            "json_schema": ".schema.json",
            "db_hints": ".db.json",
        }
        
        for name, content in results.items():
            filepath = os.path.join(output_dir, f"{schema.__name__}{extensions[name]}")
            with open(filepath, "w") as f:
                f.write(content)
    
    return results
