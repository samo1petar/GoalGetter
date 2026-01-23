"""
Authentication API endpoints.
Handles user registration, login, OAuth, and token management.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_database
from app.core.security import get_current_user, get_current_active_user, security
from app.services.auth_service import AuthService
from app.schemas.user import (
    UserCreate,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    Token,
    AccessToken,
    UserResponse,
    PasswordResetRequest,
    PasswordResetConfirm,
    Enable2FAResponse,
    Verify2FARequest,
    LoginWith2FARequest
)
from typing import Union

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


@router.post("/login")
@limiter.limit("10/minute")  # Strict limit on login attempts
async def login(
    request: Request,
    login_data: LoginWith2FARequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Login with email and password, with optional 2FA support.

    - **email**: User's email address
    - **password**: User's password
    - **totp_code**: Optional 2FA code (required if 2FA is enabled)

    Returns user info and authentication tokens, or requires_2fa: true if 2FA is needed.
    Rate limit: 10 requests per minute.
    """
    auth_service = AuthService(db)
    result = await auth_service.login_user_with_2fa(login_data, login_data.totp_code)
    return result


@router.post("/refresh", response_model=AccessToken)
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
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Logout current user by blacklisting their access token.

    The token will be added to Redis blacklist with TTL matching the token's
    remaining lifetime. This ensures the token cannot be reused even if stolen.

    Additionally, extracts and saves session context for AI Coach memory.
    """
    import logging
    from datetime import datetime
    from app.core.security import SecurityUtils
    from app.core.redis import RedisClient

    logger = logging.getLogger(__name__)

    token = credentials.credentials
    payload = SecurityUtils.verify_token(token, token_type="access")
    jti = payload.get("jti")
    exp = payload.get("exp")

    if jti and exp:
        # Calculate TTL as remaining token lifetime
        ttl = int(exp - datetime.utcnow().timestamp())
        if ttl > 0:
            await RedisClient.blacklist_token(jti, ttl)

    # Queue context extraction as background task (non-blocking)
    from app.tasks.celery_tasks import extract_session_context_task

    session_id = jti or f"logout-{datetime.utcnow().timestamp()}"
    extract_session_context_task.delay(
        user_id=current_user["id"],
        session_id=session_id,
    )
    logger.info(f"Queued context extraction for user {current_user['id']}")

    return {
        "message": "Successfully logged out",
        "detail": "Your access token has been invalidated"
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


@router.post("/forgot-password")
@limiter.limit("3/minute")  # Strict limit to prevent abuse
async def forgot_password(
    request: Request,
    data: PasswordResetRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Request a password reset email.

    - **email**: Email address to send reset link to

    Always returns success to prevent email enumeration attacks.
    Rate limit: 3 requests per minute.
    """
    auth_service = AuthService(db)
    await auth_service.request_password_reset(data.email)

    # Always return success to prevent email enumeration
    return {
        "message": "If an account exists with this email, you will receive a password reset link."
    }


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    data: PasswordResetConfirm,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Reset password using token from email.

    - **token**: Reset token from the email link
    - **new_password**: New password (min 8 characters)

    Rate limit: 5 requests per minute.
    """
    auth_service = AuthService(db)
    await auth_service.confirm_password_reset(data.token, data.new_password)

    return {"message": "Password has been reset successfully. You can now log in."}


# Two-Factor Authentication Routes

@router.post("/2fa/setup", response_model=Enable2FAResponse)
async def setup_2fa(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Setup 2FA for current user.

    Returns secret key, QR code URI, and backup codes.
    User must verify the setup by providing a valid code.
    """
    auth_service = AuthService(db)
    return await auth_service.setup_2fa(current_user["id"])


@router.post("/2fa/verify")
async def verify_2fa(
    data: Verify2FARequest,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Verify and enable 2FA.

    - **code**: 6-digit code from authenticator app

    Call this after setup to confirm 2FA is working.
    """
    auth_service = AuthService(db)
    await auth_service.verify_and_enable_2fa(current_user["id"], data.code)
    return {"message": "Two-factor authentication enabled successfully"}


@router.post("/2fa/disable")
async def disable_2fa(
    data: Verify2FARequest,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Disable 2FA for current user.

    - **code**: 6-digit code from authenticator app or backup code

    Requires valid 2FA code to disable.
    """
    auth_service = AuthService(db)
    await auth_service.disable_2fa(current_user["id"], data.code)
    return {"message": "Two-factor authentication disabled successfully"}
