"""
Custom exception classes for GoalGetter API.
Provides structured error handling with consistent error responses.
"""
from typing import Any, Dict, Optional


class GoalGetterException(Exception):
    """Base exception class for all GoalGetter errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response."""
        error_dict = {
            "error": self.error_code,
            "message": self.message,
        }
        if self.details:
            error_dict["details"] = self.details
        return error_dict


# Authentication Exceptions
class AuthenticationError(GoalGetterException):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        error_code: str = "AUTH_FAILED",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=401,
            error_code=error_code,
            details=details,
        )


class InvalidCredentialsError(AuthenticationError):
    """Raised when login credentials are invalid."""

    def __init__(self, message: str = "Invalid email or password"):
        super().__init__(
            message=message,
            error_code="INVALID_CREDENTIALS",
        )


class TokenExpiredError(AuthenticationError):
    """Raised when a token has expired."""

    def __init__(self, message: str = "Token has expired"):
        super().__init__(
            message=message,
            error_code="TOKEN_EXPIRED",
        )


class InvalidTokenError(AuthenticationError):
    """Raised when a token is invalid."""

    def __init__(self, message: str = "Invalid token"):
        super().__init__(
            message=message,
            error_code="INVALID_TOKEN",
        )


class TokenBlacklistedError(AuthenticationError):
    """Raised when a token has been blacklisted."""

    def __init__(self, message: str = "Token has been revoked"):
        super().__init__(
            message=message,
            error_code="TOKEN_REVOKED",
        )


# Authorization Exceptions
class AuthorizationError(GoalGetterException):
    """Raised when user lacks permission for an action."""

    def __init__(
        self,
        message: str = "You don't have permission to perform this action",
        error_code: str = "FORBIDDEN",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=403,
            error_code=error_code,
            details=details,
        )


class ChatAccessDeniedError(AuthorizationError):
    """Raised when user cannot access chat."""

    def __init__(
        self,
        message: str = "Chat access is not available",
        next_available: Optional[str] = None,
    ):
        details = {}
        if next_available:
            details["next_available"] = next_available
        super().__init__(
            message=message,
            error_code="CHAT_ACCESS_DENIED",
            details=details,
        )


# Resource Exceptions
class NotFoundError(GoalGetterException):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        resource: str = "Resource",
        resource_id: Optional[str] = None,
        message: Optional[str] = None,
    ):
        if message is None:
            if resource_id:
                message = f"{resource} with ID '{resource_id}' not found"
            else:
                message = f"{resource} not found"
        super().__init__(
            message=message,
            status_code=404,
            error_code="NOT_FOUND",
            details={"resource": resource, "resource_id": resource_id} if resource_id else {"resource": resource},
        )


class GoalNotFoundError(NotFoundError):
    """Raised when a goal is not found."""

    def __init__(self, goal_id: str):
        super().__init__(resource="Goal", resource_id=goal_id)


class MeetingNotFoundError(NotFoundError):
    """Raised when a meeting is not found."""

    def __init__(self, meeting_id: str):
        super().__init__(resource="Meeting", resource_id=meeting_id)


class UserNotFoundError(NotFoundError):
    """Raised when a user is not found."""

    def __init__(self, user_id: Optional[str] = None):
        super().__init__(resource="User", resource_id=user_id)


class TemplateNotFoundError(NotFoundError):
    """Raised when a template is not found."""

    def __init__(self, template_type: str):
        super().__init__(
            resource="Template",
            resource_id=template_type,
            message=f"Template '{template_type}' not found",
        )


# Validation Exceptions
class ValidationError(GoalGetterException):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str = "Validation failed",
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if field:
            error_details["field"] = field
        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            details=error_details,
        )


class DuplicateResourceError(GoalGetterException):
    """Raised when attempting to create a duplicate resource."""

    def __init__(
        self,
        resource: str = "Resource",
        field: str = "value",
        message: Optional[str] = None,
    ):
        if message is None:
            message = f"{resource} with this {field} already exists"
        super().__init__(
            message=message,
            status_code=409,
            error_code="DUPLICATE_RESOURCE",
            details={"resource": resource, "field": field},
        )


class EmailAlreadyExistsError(DuplicateResourceError):
    """Raised when attempting to register with an existing email."""

    def __init__(self):
        super().__init__(
            resource="User",
            field="email",
            message="Email is already registered",
        )


# Service Exceptions
class ServiceUnavailableError(GoalGetterException):
    """Raised when an external service is unavailable."""

    def __init__(
        self,
        service: str = "Service",
        message: Optional[str] = None,
    ):
        if message is None:
            message = f"{service} is currently unavailable"
        super().__init__(
            message=message,
            status_code=503,
            error_code="SERVICE_UNAVAILABLE",
            details={"service": service},
        )


class AIServiceError(ServiceUnavailableError):
    """Raised when the AI service (Claude) is unavailable or fails."""

    def __init__(self, message: str = "AI coaching service is temporarily unavailable"):
        super().__init__(service="AI Coach", message=message)


class CalendarServiceError(ServiceUnavailableError):
    """Raised when the calendar service is unavailable."""

    def __init__(self, message: str = "Calendar service is temporarily unavailable"):
        super().__init__(service="Calendar", message=message)


class EmailServiceError(ServiceUnavailableError):
    """Raised when the email service is unavailable."""

    def __init__(self, message: str = "Email service is temporarily unavailable"):
        super().__init__(service="Email", message=message)


# Feature Exceptions
class FeatureDisabledError(GoalGetterException):
    """Raised when a feature is disabled."""

    def __init__(
        self,
        feature: str,
        message: Optional[str] = None,
    ):
        if message is None:
            message = f"{feature} is not enabled"
        super().__init__(
            message=message,
            status_code=501,
            error_code="FEATURE_DISABLED",
            details={"feature": feature},
        )


class OAuthNotConfiguredError(FeatureDisabledError):
    """Raised when OAuth is not configured."""

    def __init__(self, provider: str = "OAuth"):
        super().__init__(
            feature=f"{provider} authentication",
            message=f"{provider} authentication is not configured",
        )


class PDFExportDisabledError(FeatureDisabledError):
    """Raised when PDF export is disabled."""

    def __init__(self):
        super().__init__(
            feature="PDF Export",
            message="PDF export feature is not enabled",
        )


# Business Logic Exceptions
class BusinessLogicError(GoalGetterException):
    """Raised when a business rule is violated."""

    def __init__(
        self,
        message: str,
        error_code: str = "BUSINESS_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=400,
            error_code=error_code,
            details=details,
        )


class InvalidPhaseTransitionError(BusinessLogicError):
    """Raised when an invalid phase transition is attempted."""

    def __init__(
        self,
        current_phase: str,
        target_phase: str,
    ):
        super().__init__(
            message=f"Cannot transition from '{current_phase}' to '{target_phase}'",
            error_code="INVALID_PHASE_TRANSITION",
            details={"current_phase": current_phase, "target_phase": target_phase},
        )


class MeetingStatusError(BusinessLogicError):
    """Raised when a meeting operation is not allowed due to status."""

    def __init__(
        self,
        operation: str,
        current_status: str,
    ):
        super().__init__(
            message=f"Cannot {operation} a meeting with status '{current_status}'",
            error_code="INVALID_MEETING_STATUS",
            details={"operation": operation, "current_status": current_status},
        )


class GoalPhaseError(BusinessLogicError):
    """Raised when a goal operation is not allowed due to phase."""

    def __init__(
        self,
        operation: str,
        current_phase: str,
    ):
        super().__init__(
            message=f"Cannot {operation} a goal in '{current_phase}' phase",
            error_code="INVALID_GOAL_PHASE",
            details={"operation": operation, "current_phase": current_phase},
        )


# Rate Limiting Exception
class RateLimitExceededError(GoalGetterException):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        retry_after: Optional[int] = None,
        message: str = "Too many requests. Please try again later.",
    ):
        details = {}
        if retry_after:
            details["retry_after_seconds"] = retry_after
        super().__init__(
            message=message,
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details=details,
        )


# Database Exceptions
class DatabaseError(GoalGetterException):
    """Raised when a database operation fails."""

    def __init__(
        self,
        message: str = "A database error occurred",
        operation: Optional[str] = None,
    ):
        details = {}
        if operation:
            details["operation"] = operation
        super().__init__(
            message=message,
            status_code=500,
            error_code="DATABASE_ERROR",
            details=details,
        )


class ConnectionError(DatabaseError):
    """Raised when database connection fails."""

    def __init__(self, database: str = "database"):
        super().__init__(
            message=f"Failed to connect to {database}",
            operation="connect",
        )
