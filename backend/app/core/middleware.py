"""
Middleware for GoalGetter API.
Provides security headers, request logging, and request ID tracking.
"""
import logging
import time
import uuid
from typing import Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.core.config import settings
from app.core.logging_config import log_api_request

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Cache control for API responses
        if not response.headers.get("Cache-Control"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"

        # Strict Transport Security (only in production with HTTPS)
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        # Content Security Policy
        response.headers["Content-Security-Policy"] = "default-src 'self'"

        # Permissions Policy
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        )

        return response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to each request."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        # Check for existing request ID (from load balancer, etc.)
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Store in request state for use in handlers
        request.state.request_id = request_id

        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all API requests with timing information."""

    # Paths to skip logging
    SKIP_PATHS = {"/health", "/", "/favicon.ico"}

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        # Skip logging for certain paths
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        # Record start time
        start_time = time.perf_counter()

        # Get request ID if available
        request_id = getattr(request.state, "request_id", None)

        # Get user ID from request state if authenticated
        user_id = None
        if hasattr(request.state, "user"):
            user_id = getattr(request.state.user, "id", None)

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            raise
        finally:
            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log the request
            log_api_request(
                logger=logger,
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                duration_ms=duration_ms,
                user_id=user_id,
                request_id=request_id,
            )

        return response


class TrustedHostMiddleware(BaseHTTPMiddleware):
    """Validate that requests come from trusted hosts."""

    def __init__(self, app: ASGIApp, allowed_hosts: list[str] = None):
        super().__init__(app)
        self.allowed_hosts = allowed_hosts or ["*"]

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        # Skip validation if all hosts are allowed
        if "*" in self.allowed_hosts:
            return await call_next(request)

        host = request.headers.get("host", "").split(":")[0]

        if host not in self.allowed_hosts:
            logger.warning(
                f"Request from untrusted host blocked: {host}",
                extra={
                    "event_type": "security",
                    "security_event": "untrusted_host_blocked",
                    "host": host,
                },
            )
            return Response(
                content="Invalid host header",
                status_code=400,
            )

        return await call_next(request)


def register_middleware(app: FastAPI) -> None:
    """Register all middleware with the FastAPI app."""
    # Order matters! Last added = first executed

    # Request logging (runs first to time everything)
    app.add_middleware(RequestLoggingMiddleware)

    # Request ID (needed by logging)
    app.add_middleware(RequestIdMiddleware)

    # Security headers (runs last, adds headers to response)
    app.add_middleware(SecurityHeadersMiddleware)

    logger.info("Middleware registered")
