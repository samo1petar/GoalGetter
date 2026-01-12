"""
Application configuration using Pydantic settings.
Loads configuration from environment variables.
"""
from typing import List, Optional, Union
from pydantic import Field, field_validator, BeforeValidator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Annotated


def parse_cors(v: Union[str, List[str]]) -> List[str]:
    """Parse CORS origins from comma-separated string or list."""
    if isinstance(v, str):
        return [origin.strip() for origin in v.split(",")]
    return v


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "GoalGetter"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_VERSION: str = "v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Security
    SECRET_KEY: str = Field(..., min_length=32)
    JWT_SECRET_KEY: str = Field(..., min_length=32)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS (comma-separated string)
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> List[str]:
        """Get CORS origins as list."""
        return parse_cors(self.BACKEND_CORS_ORIGINS)

    # Database - MongoDB
    MONGODB_URI: str = "mongodb://localhost:27017/goalgetter"
    MONGODB_DB_NAME: str = "goalgetter"
    MONGODB_MIN_POOL_SIZE: int = 10
    MONGODB_MAX_POOL_SIZE: int = 50

    # Database - Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 50

    # Anthropic Claude API
    ANTHROPIC_API_KEY: Optional[str] = None  # Required for Sprint 3+
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    ANTHROPIC_MAX_TOKENS: int = 4096
    ANTHROPIC_TEMPERATURE: float = 0.7

    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"

    # Google Calendar
    GOOGLE_CALENDAR_SCOPES: str = "https://www.googleapis.com/auth/calendar"

    # Email - SendGrid
    SENDGRID_API_KEY: Optional[str] = None
    FROM_EMAIL: str = "noreply@goalgetter.com"
    FROM_NAME: str = "GoalGetter"
    SUPPORT_EMAIL: str = "support@goalgetter.com"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_TIMEZONE: str = "UTC"
    CELERY_ENABLE_UTC: bool = True

    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"

    # File Upload
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_FILE_TYPES: str = "pdf,doc,docx,txt,jpg,jpeg,png"

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # Monitoring - Sentry
    SENTRY_DSN: Optional[str] = None
    SENTRY_ENVIRONMENT: str = "development"
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # Meeting Settings
    DEFAULT_MEETING_DURATION_MINUTES: int = 30
    MEETING_WINDOW_BEFORE_MINUTES: int = 30
    MEETING_WINDOW_AFTER_MINUTES: int = 60
    DEFAULT_MEETING_INTERVAL_DAYS: int = 7

    # Feature Flags
    ENABLE_CALENDAR_SYNC: bool = True
    ENABLE_EMAIL_NOTIFICATIONS: bool = True
    ENABLE_PDF_EXPORT: bool = True

    # Cache Settings
    CACHE_TTL_SECONDS: int = 3600
    CACHE_USER_PROFILE_TTL: int = 3600
    CACHE_GOALS_TTL: int = 300
    CACHE_MEETINGS_TTL: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        env_parse_enums=False
    )

    @property
    def api_prefix(self) -> str:
        """Get API prefix with version."""
        return f"/api/{self.API_VERSION}"

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.APP_ENV == "development"


# Global settings instance
settings = Settings()
