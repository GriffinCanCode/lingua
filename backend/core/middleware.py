"""Request Middleware for Logging and Tracing

Provides:
- Request correlation IDs for tracing
- Request/response logging with timing
- Context propagation for structured logs
"""
import time
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from core.logging import (
    generate_correlation_id,
    bind_context,
    clear_context,
    api_logger,
)

log = api_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs requests/responses and manages correlation context."""
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Generate or extract correlation ID
        correlation_id = request.headers.get("X-Correlation-ID") or generate_correlation_id()
        
        # Set up logging context for this request
        clear_context()
        bind_context(
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown",
        )
        
        # Extract user agent for debugging
        user_agent = request.headers.get("User-Agent", "")[:100]  # Truncate
        
        start = time.perf_counter()
        
        # Log request start
        log.info(
            "request_started",
            query=str(request.query_params) if request.query_params else None,
            user_agent=user_agent,
        )
        
        # Process request
        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start) * 1000
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            
            # Log based on status
            status = response.status_code
            log_method = log.info if status < 400 else (log.warning if status < 500 else log.error)
            log_method(
                "request_completed",
                status=status,
                duration_ms=round(duration_ms, 2),
            )
            
            return response
            
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            log.exception(
                "request_failed",
                error=str(exc),
                error_type=type(exc).__name__,
                duration_ms=round(duration_ms, 2),
            )
            raise
        finally:
            clear_context()


class SlowRequestMiddleware(BaseHTTPMiddleware):
    """Middleware that warns about slow requests."""
    
    def __init__(self, app, slow_threshold_ms: float = 1000):
        super().__init__(app)
        self.slow_threshold_ms = slow_threshold_ms
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        
        if duration_ms > self.slow_threshold_ms:
            log.warning(
                "slow_request",
                duration_ms=round(duration_ms, 2),
                threshold_ms=self.slow_threshold_ms,
            )
        
        return response

