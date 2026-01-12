"""
GoalGetter - AI-Powered Goal Achievement Platform
Main FastAPI application entry point.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.database import Database
from app.core.redis import RedisClient
from app.core.logging_config import setup_logging, get_logger
from app.core.exception_handlers import register_exception_handlers
from app.core.middleware import register_middleware
from app.api.routes import auth, goals, templates, chat, meetings, users

# Setup structured logging
setup_logging()
logger = get_logger(__name__)

# Initialize rate limiter
# Uses Redis for distributed rate limiting in production
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
    storage_uri=settings.REDIS_URL if not settings.DEBUG else None,
    strategy="fixed-window",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(
        "Application starting",
        extra={
            "event_type": "app_lifecycle",
            "app_name": settings.APP_NAME,
            "environment": settings.APP_ENV,
            "debug_mode": settings.DEBUG,
            "api_version": settings.API_VERSION,
        },
    )

    # Initialize Sentry if configured
    if settings.SENTRY_DSN:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            from sentry_sdk.integrations.starlette import StarletteIntegration

            sentry_sdk.init(
                dsn=settings.SENTRY_DSN,
                environment=settings.SENTRY_ENVIRONMENT,
                traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
                integrations=[
                    StarletteIntegration(transaction_style="endpoint"),
                    FastApiIntegration(transaction_style="endpoint"),
                ],
            )
            logger.info(
                "Sentry initialized",
                extra={
                    "event_type": "external_service",
                    "service": "sentry",
                    "environment": settings.SENTRY_ENVIRONMENT,
                },
            )
        except ImportError:
            logger.warning("Sentry SDK not installed, skipping Sentry initialization")
        except Exception as e:
            logger.error(f"Failed to initialize Sentry: {e}")

    # Initialize database connections
    try:
        await Database.connect_db()
        logger.info(
            "MongoDB connected",
            extra={
                "event_type": "database",
                "database": "mongodb",
                "status": "connected",
            },
        )
    except Exception as e:
        logger.error(
            f"Failed to connect to MongoDB: {e}",
            extra={
                "event_type": "database",
                "database": "mongodb",
                "status": "failed",
            },
        )
        raise

    try:
        await RedisClient.connect_redis()
        logger.info(
            "Redis connected",
            extra={
                "event_type": "database",
                "database": "redis",
                "status": "connected",
            },
        )
    except Exception as e:
        logger.error(
            f"Failed to connect to Redis: {e}",
            extra={
                "event_type": "database",
                "database": "redis",
                "status": "failed",
            },
        )
        raise

    logger.info(
        "Application started successfully",
        extra={
            "event_type": "app_lifecycle",
            "status": "started",
        },
    )

    yield

    # Shutdown
    logger.info(
        "Application shutting down",
        extra={
            "event_type": "app_lifecycle",
            "status": "shutting_down",
        },
    )

    await Database.close_db()
    await RedisClient.close_redis()

    logger.info(
        "Application shutdown complete",
        extra={
            "event_type": "app_lifecycle",
            "status": "stopped",
        },
    )


# API description for OpenAPI docs
API_DESCRIPTION = """
## GoalGetter API

GoalGetter is an AI-powered goal achievement platform that helps users set and achieve
meaningful goals through personalized coaching with a Tony Robbins-inspired AI coach.

### Features

- **Goal Management**: Create, update, and track goals using SMART and OKR frameworks
- **AI Coaching**: Real-time chat with an AI coach that provides motivation and guidance
- **Meeting Scheduling**: Schedule regular check-ins with your AI coach
- **PDF Export**: Export your goals as formatted PDF documents
- **Email Notifications**: Receive reminders for upcoming meetings

### Phases

1. **Goal Setting Phase**: Unlimited access to the AI coach for collaborative goal creation
2. **Tracking Phase**: Scheduled meetings with the coach to review progress

### Authentication

Most endpoints require JWT authentication. Obtain tokens via:
- `POST /api/v1/auth/signup` - Create a new account
- `POST /api/v1/auth/login` - Login with email/password
- `GET /api/v1/auth/google` - OAuth with Google

Include the token in the Authorization header:
```
Authorization: Bearer <your_token>
```

### Rate Limiting

API requests are rate-limited to ensure fair usage:
- Default: 60 requests per minute
- Auth endpoints: 5-10 requests per minute
- Chat endpoints: 30 requests per minute

### WebSocket

Real-time chat is available via WebSocket at `/api/v1/chat/ws`

Connect with your JWT token as a query parameter:
```
ws://localhost:8000/api/v1/chat/ws?token=<your_token>
```
"""

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description=API_DESCRIPTION,
    version=settings.API_VERSION,
    docs_url=f"{settings.api_prefix}/docs",
    redoc_url=f"{settings.api_prefix}/redoc",
    openapi_url=f"{settings.api_prefix}/openapi.json",
    lifespan=lifespan,
    debug=settings.DEBUG,
    openapi_tags=[
        {
            "name": "Authentication",
            "description": "User registration, login, and OAuth authentication",
        },
        {
            "name": "Goals",
            "description": "Goal CRUD operations, templates, and PDF export",
        },
        {
            "name": "Templates",
            "description": "Goal templates (SMART, OKR frameworks)",
        },
        {
            "name": "Chat",
            "description": "AI coaching chat via WebSocket and REST",
        },
        {
            "name": "Meetings",
            "description": "Meeting scheduling and management",
        },
        {
            "name": "Users",
            "description": "User profile and preferences management",
        },
    ],
    contact={
        "name": "GoalGetter Support",
        "email": settings.SUPPORT_EMAIL,
    },
    license_info={
        "name": "Proprietary",
    },
)

# Add rate limiter to app state and exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Register custom exception handlers
register_exception_handlers(app)

# Register middleware
register_middleware(app)

# Configure CORS - must be added after other middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Request-ID",
        "Accept",
        "Origin",
        "X-Requested-With",
    ],
    expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
    max_age=600,  # Cache preflight requests for 10 minutes
)


# Root endpoint
@app.get(
    "/",
    summary="API Information",
    description="Returns basic information about the API including version and documentation URL.",
    response_description="API information object",
    tags=["Root"],
)
async def root():
    """
    Get API information.

    Returns the API name, version, environment, and documentation URL.
    This endpoint does not require authentication.
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.API_VERSION,
        "environment": settings.APP_ENV,
        "status": "running",
        "docs": f"{settings.api_prefix}/docs",
    }


# Health check endpoint
@app.get(
    "/health",
    summary="Health Check",
    description="Health check endpoint for load balancers and monitoring systems.",
    response_description="Health status object",
    tags=["Root"],
)
async def health_check():
    """
    Check API health status.

    Returns a simple health status. Use this endpoint for:
    - Load balancer health checks
    - Kubernetes liveness probes
    - Monitoring systems

    This endpoint does not require authentication.
    """
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.API_VERSION,
    }


# Detailed status endpoint
@app.get(
    "/status",
    summary="Detailed Status",
    description="Returns detailed status including enabled features.",
    response_description="Detailed status object",
    tags=["Root"],
)
async def status():
    """
    Get detailed API status.

    Returns:
    - Application name and version
    - Current environment
    - Enabled features (calendar sync, email notifications, PDF export)

    This endpoint does not require authentication.
    """
    return {
        "app": settings.APP_NAME,
        "version": settings.API_VERSION,
        "environment": settings.APP_ENV,
        "status": "operational",
        "features": {
            "calendar_sync": settings.ENABLE_CALENDAR_SYNC,
            "email_notifications": settings.ENABLE_EMAIL_NOTIFICATIONS,
            "pdf_export": settings.ENABLE_PDF_EXPORT,
        },
    }


# Include routers with enhanced descriptions
app.include_router(
    auth.router,
    prefix=f"{settings.api_prefix}/auth",
    tags=["Authentication"],
)
app.include_router(
    goals.router,
    prefix=f"{settings.api_prefix}/goals",
    tags=["Goals"],
)
app.include_router(
    templates.router,
    prefix=f"{settings.api_prefix}/templates",
    tags=["Templates"],
)
app.include_router(
    chat.router,
    prefix=f"{settings.api_prefix}/chat",
    tags=["Chat"],
)
app.include_router(
    meetings.router,
    prefix=f"{settings.api_prefix}/meetings",
    tags=["Meetings"],
)
app.include_router(
    users.router,
    prefix=f"{settings.api_prefix}/users",
    tags=["Users"],
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
