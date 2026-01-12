"""
GoalGetter - AI-Powered Goal Achievement Platform
Main FastAPI application entry point.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME} API")
    logger.info(f"Environment: {settings.APP_ENV}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    # TODO: Initialize database connections
    # TODO: Initialize Redis connection
    # TODO: Initialize Sentry if configured

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME} API")
    # TODO: Close database connections
    # TODO: Close Redis connection


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered goal setting and tracking platform with Tony Robbins coaching",
    version=settings.API_VERSION,
    docs_url=f"{settings.api_prefix}/docs",
    redoc_url=f"{settings.api_prefix}/redoc",
    openapi_url=f"{settings.api_prefix}/openapi.json",
    lifespan=lifespan,
    debug=settings.DEBUG,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.API_VERSION,
        "environment": settings.APP_ENV,
        "status": "running",
        "docs": f"{settings.api_prefix}/docs"
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.API_VERSION
    }


# Status endpoint with more details
@app.get("/status")
async def status():
    """Detailed status endpoint."""
    return {
        "app": settings.APP_NAME,
        "version": settings.API_VERSION,
        "environment": settings.APP_ENV,
        "status": "operational",
        "features": {
            "calendar_sync": settings.ENABLE_CALENDAR_SYNC,
            "email_notifications": settings.ENABLE_EMAIL_NOTIFICATIONS,
            "pdf_export": settings.ENABLE_PDF_EXPORT
        }
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.DEBUG else "An unexpected error occurred"
        }
    )


# TODO: Include routers
# from app.api.routes import auth, users, goals, chat, meetings, calendar, templates
# app.include_router(auth.router, prefix=f"{settings.api_prefix}/auth", tags=["Authentication"])
# app.include_router(users.router, prefix=f"{settings.api_prefix}/users", tags=["Users"])
# app.include_router(goals.router, prefix=f"{settings.api_prefix}/goals", tags=["Goals"])
# app.include_router(chat.router, prefix=f"{settings.api_prefix}/chat", tags=["Chat"])
# app.include_router(meetings.router, prefix=f"{settings.api_prefix}/meetings", tags=["Meetings"])
# app.include_router(calendar.router, prefix=f"{settings.api_prefix}/calendar", tags=["Calendar"])
# app.include_router(templates.router, prefix=f"{settings.api_prefix}/templates", tags=["Templates"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
