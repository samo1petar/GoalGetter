"""
Structured logging configuration for GoalGetter API.
Provides JSON logging for production and human-readable format for development.
"""
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional

from pythonjsonlogger import jsonlogger

from app.core.config import settings


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields."""

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any],
    ) -> None:
        super().add_fields(log_record, record, message_dict)

        # Add timestamp in ISO format
        log_record["timestamp"] = datetime.utcnow().isoformat() + "Z"

        # Add standard fields
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["app"] = settings.APP_NAME
        log_record["environment"] = settings.APP_ENV

        # Add location info
        log_record["module"] = record.module
        log_record["function"] = record.funcName
        log_record["line"] = record.lineno

        # Add exception info if present
        if record.exc_info:
            log_record["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
            }

        # Clean up fields that are handled differently
        fields_to_remove = ["color_message", "asctime"]
        for field in fields_to_remove:
            log_record.pop(field, None)


class RequestIdFilter(logging.Filter):
    """Filter to add request ID to log records."""

    def __init__(self, request_id: Optional[str] = None):
        super().__init__()
        self.request_id = request_id

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = getattr(record, "request_id", self.request_id or "-")
        return True


def setup_logging() -> None:
    """Configure logging based on environment."""
    # Determine log level
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # Choose formatter based on environment
    if settings.LOG_FORMAT.lower() == "json" or settings.is_production:
        # JSON format for production
        formatter = CustomJsonFormatter(
            fmt="%(timestamp)s %(level)s %(name)s %(message)s",
            json_ensure_ascii=False,
        )
    else:
        # Human-readable format for development
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler.setFormatter(formatter)

    # Add request ID filter
    console_handler.addFilter(RequestIdFilter())

    # Add handler to root logger
    root_logger.addHandler(console_handler)

    # Set log levels for noisy libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.ERROR)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)

    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured",
        extra={
            "log_level": settings.LOG_LEVEL,
            "log_format": settings.LOG_FORMAT,
            "environment": settings.APP_ENV,
        },
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(name)


class LoggerAdapter(logging.LoggerAdapter):
    """Custom logger adapter with context support."""

    def process(
        self, msg: str, kwargs: Dict[str, Any]
    ) -> tuple[str, Dict[str, Any]]:
        # Merge extra context
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs


def get_context_logger(
    name: str,
    **context: Any,
) -> LoggerAdapter:
    """Get a logger with additional context."""
    logger = logging.getLogger(name)
    return LoggerAdapter(logger, context)


# Event logging helpers
def log_user_action(
    logger: logging.Logger,
    action: str,
    user_id: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Log a user action with structured data."""
    extra = {
        "event_type": "user_action",
        "action": action,
        "user_id": user_id,
    }
    if resource_type:
        extra["resource_type"] = resource_type
    if resource_id:
        extra["resource_id"] = resource_id
    if details:
        extra["details"] = details

    logger.info(f"User action: {action}", extra=extra)


def log_api_request(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> None:
    """Log an API request with structured data."""
    extra = {
        "event_type": "api_request",
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2),
    }
    if user_id:
        extra["user_id"] = user_id
    if request_id:
        extra["request_id"] = request_id

    # Choose log level based on status code
    if status_code >= 500:
        logger.error(f"{method} {path} {status_code} ({duration_ms:.0f}ms)", extra=extra)
    elif status_code >= 400:
        logger.warning(f"{method} {path} {status_code} ({duration_ms:.0f}ms)", extra=extra)
    else:
        logger.info(f"{method} {path} {status_code} ({duration_ms:.0f}ms)", extra=extra)


def log_security_event(
    logger: logging.Logger,
    event: str,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Log a security-related event."""
    extra = {
        "event_type": "security",
        "security_event": event,
    }
    if user_id:
        extra["user_id"] = user_id
    if ip_address:
        extra["ip_address"] = ip_address
    if details:
        extra["details"] = details

    logger.warning(f"Security event: {event}", extra=extra)


def log_external_service(
    logger: logging.Logger,
    service: str,
    operation: str,
    success: bool,
    duration_ms: Optional[float] = None,
    error: Optional[str] = None,
) -> None:
    """Log an external service call."""
    extra = {
        "event_type": "external_service",
        "service": service,
        "operation": operation,
        "success": success,
    }
    if duration_ms is not None:
        extra["duration_ms"] = round(duration_ms, 2)
    if error:
        extra["error"] = error

    if success:
        logger.info(f"External service: {service}.{operation} succeeded", extra=extra)
    else:
        logger.error(f"External service: {service}.{operation} failed", extra=extra)
