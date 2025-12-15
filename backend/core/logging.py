"""Structured Logging System for Lingua Backend

Modern 2025-style logging with:
- Colored, human-readable dev output
- JSON structured production output  
- Request correlation/tracing IDs
- Context propagation
- Extensible processors for future integrations (OpenTelemetry, etc.)
"""
import logging
import sys
from contextvars import ContextVar
from typing import Callable
from uuid import uuid4

import structlog
from structlog.types import EventDict, Processor

# Context variable for request-scoped data (correlation ID, user context, etc.)
request_context: ContextVar[dict] = ContextVar("request_context", default={})


def _add_request_context(
    logger: logging.Logger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Processor that injects request context into log events."""
    ctx = request_context.get()
    if ctx:
        event_dict.update(ctx)
    return event_dict


def _censor_sensitive_keys(
    logger: logging.Logger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Processor that redacts sensitive information."""
    sensitive_keys = {"password", "token", "secret", "authorization", "cookie", "hashed_password"}
    
    def _redact(obj: dict | list | str, depth: int = 0) -> dict | list | str:
        if depth > 5:  # Prevent infinite recursion
            return obj
        if isinstance(obj, dict):
            return {
                k: "[REDACTED]" if k.lower() in sensitive_keys else _redact(v, depth + 1)
                for k, v in obj.items()
            }
        if isinstance(obj, list):
            return [_redact(item, depth + 1) for item in obj]
        return obj
    
    return _redact(event_dict)


def _add_service_info(
    logger: logging.Logger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Processor that adds service metadata."""
    event_dict.setdefault("service", "lingua-backend")
    event_dict.setdefault("version", "0.1.0")
    return event_dict


def _drop_color_message_key(
    logger: logging.Logger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Drop internal structlog key that's added for colored console output."""
    event_dict.pop("_color_message", None)
    return event_dict


def get_shared_processors() -> list[Processor]:
    """Processors used in both dev and prod configurations."""
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        _add_request_context,
        _add_service_info,
        _censor_sensitive_keys,
    ]


def configure_logging(
    level: str = "INFO",
    json_logs: bool = False,
    log_sql: bool = False,
) -> None:
    """Configure the logging system.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: If True, output JSON format (for production). If False, colored console output.
        log_sql: If True, enable SQLAlchemy SQL statement logging.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    shared_processors = get_shared_processors()
    
    if json_logs:
        # Production: JSON output
        renderer = structlog.processors.JSONRenderer()
    else:
        # Development: colored, human-readable output
        renderer = structlog.dev.ConsoleRenderer(
            colors=True,
            exception_formatter=structlog.dev.plain_traceback,
        )
    
    # Formatter for stdlib logger (handles logs from third-party libs)
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(log_level)
    
    # Set third-party library log levels
    for logger_name in ["uvicorn", "uvicorn.error"]:
        logging.getLogger(logger_name).handlers = []
    
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    # SQLAlchemy logging
    sa_level = logging.DEBUG if log_sql else logging.WARNING
    logging.getLogger("sqlalchemy.engine").setLevel(sa_level)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)


def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__ from the calling module)
    
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


def generate_correlation_id() -> str:
    """Generate a unique correlation ID for request tracing."""
    return str(uuid4())[:8]


def bind_context(**kwargs) -> None:
    """Bind key-value pairs to the current logging context.
    
    These will appear in all subsequent log messages within this context.
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """Clear all bound context variables."""
    structlog.contextvars.clear_contextvars()


def unbind_context(*keys: str) -> None:
    """Remove specific keys from the logging context."""
    structlog.contextvars.unbind_contextvars(*keys)


# Pre-configured loggers for common domains
class LoggerRegistry:
    """Registry of pre-configured loggers for different application domains."""
    
    _loggers: dict[str, structlog.stdlib.BoundLogger] = {}
    
    @classmethod
    def get(cls, name: str) -> structlog.stdlib.BoundLogger:
        """Get or create a logger for the given domain."""
        if name not in cls._loggers:
            cls._loggers[name] = get_logger(f"lingua.{name}")
        return cls._loggers[name]


# Convenience accessors for common loggers
def api_logger() -> structlog.stdlib.BoundLogger:
    """Logger for API layer events."""
    return LoggerRegistry.get("api")


def engine_logger() -> structlog.stdlib.BoundLogger:
    """Logger for engine/processing events."""
    return LoggerRegistry.get("engine")


def db_logger() -> structlog.stdlib.BoundLogger:
    """Logger for database operations."""
    return LoggerRegistry.get("db")


def auth_logger() -> structlog.stdlib.BoundLogger:
    """Logger for authentication/security events."""
    return LoggerRegistry.get("auth")


def srs_logger() -> structlog.stdlib.BoundLogger:
    """Logger for SRS (spaced repetition) events."""
    return LoggerRegistry.get("srs")

