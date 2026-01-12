"""
Authentication API endpoints.
Handles user registration, login, OAuth, and token management.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import RedirectResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_database
from app.core.security import get_current_user, get_current_active_user
from app.services.auth_service import AuthService
from app.schemas.user import (
    UserCreate,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    Token,
    UserResponse
)

router = APIRouter()

# Rate limiter for auth endpoints (stricter limits)
limiter = Limiter(key_func=get_remote_address)


@router.post("/signup", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")  # Strict limit on signups
async def signup(
    request: Request,
    user_data: UserCreate,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Register a new user with email and password.

    - **email**: User's email address (must be unique)
    - **name**: User's full name
    - **password**: Password (min 8 characters)

    Returns user info and authentication tokens.
    Rate limit: 5 requests per minute.
    """
    auth_service = AuthService(db)
    result = await auth_service.register_user(user_data)
    return result


@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")  # Strict limit on login attempts
async def login(
    request: Request,
    login_data: LoginRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Login with email and password.

    - **email**: User's email address
    - **password**: User's password

    Returns user info and authentication tokens.
    Rate limit: 10 requests per minute.
    """
    auth_service = AuthService(db)
    result = await auth_service.login_user(login_data)
    return result


@router.post("/refresh", response_model=Token)
@limiter.limit("30/minute")  # More lenient for token refresh
async def refresh_token(
    request: Request,
    refresh_data: RefreshTokenRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Refresh access token using a refresh token.

    - **refresh_token**: Valid refresh token

    Returns new access token.
    Rate limit: 30 requests per minute.
    """
    auth_service = AuthService(db)
    result = await auth_service.refresh_access_token(refresh_data.refresh_token)
    return result


@router.get("/google")
@limiter.limit("10/minute")  # Limit OAuth initiations
async def google_oauth_login(
    request: Request,
    redirect_uri: str = Query(None, description="Optional custom redirect URI"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Initiate Google OAuth flow.

    Redirects user to Google's OAuth consent screen.
    After user approves, Google redirects to the callback URL.
    """
    auth_service = AuthService(db)
    auth_url = await auth_service.google_oauth_url(redirect_uri)
    return {"auth_url": auth_url}


@router.get("/google/callback", response_model=LoginResponse)
async def google_oauth_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(None, description="State parameter for CSRF protection"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Handle Google OAuth callback.

    This endpoint receives the authorization code from Google,
    exchanges it for user information, and creates/logs in the user.

    - **code**: Authorization code from Google (required)
    - **state**: State parameter for CSRF validation (optional)

    Returns user info and authentication tokens.
    """
    auth_service = AuthService(db)
    result = await auth_service.google_oauth_callback(code, state)
    return result


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_active_user)
):
    """
    Get current authenticated user's information.

    Requires valid JWT token in Authorization header.

    Returns current user's profile information.
    """
    return current_user


@router.post("/logout")
async def logout(
    current_user: dict = Depends(get_current_active_user)
):
    """
    Logout current user.

    Note: Since we're using JWT tokens, true logout would require
    token blacklisting in Redis. For now, the client should discard tokens.

    TODO: Implement token blacklisting in Redis for secure logout.
    """
    # TODO: Add token to Redis blacklist with TTL matching token expiration
    return {
        "message": "Successfully logged out",
        "detail": "Please discard your access and refresh tokens"
    }


@router.post("/verify-token")
async def verify_token(
    current_user: dict = Depends(get_current_user)
):
    """
    Verify if the provided token is valid.

    Requires valid JWT token in Authorization header.

    Returns token validity status and user info.
    """
    return {
        "valid": True,
        "user": current_user
    }
