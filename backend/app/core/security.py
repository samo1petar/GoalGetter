"""
Security utilities for authentication and authorization.
Includes JWT token management and password hashing.
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.database import get_database
from app.models.user import UserModel

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer for token authentication
security = HTTPBearer()


class SecurityUtils:
    """Security utilities for authentication."""

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash."""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)

    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token with unique JTI for blacklisting support."""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

        # Add unique JTI (JWT ID) for token blacklisting support
        jti = str(uuid.uuid4())
        to_encode.update({"exp": expire, "type": "access", "jti": jti})
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt

    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """Create a JWT refresh token with unique JTI for blacklisting support."""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        # Add unique JTI (JWT ID) for token blacklisting support
        jti = str(uuid.uuid4())
        to_encode.update({"exp": expire, "type": "refresh", "jti": jti})
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

            # Verify token type
            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token type. Expected {token_type}",
                )

            return payload

        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @staticmethod
    def create_token_pair(user_id: str, email: str) -> Dict[str, str]:
        """Create both access and refresh tokens for a user."""
        token_data = {"user_id": user_id, "email": email}

        access_token = SecurityUtils.create_access_token(token_data)
        refresh_token = SecurityUtils.create_refresh_token(token_data)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db = Depends(get_database)
) -> dict:
    """
    Dependency to get the current authenticated user.
    Validates JWT token and retrieves user from database.
    """
    token = credentials.credentials

    # Verify token
    payload = SecurityUtils.verify_token(token, token_type="access")
    user_id: str = payload.get("user_id")
    jti: str = payload.get("jti")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    # Check if token is blacklisted (logged out)
    if jti:
        from app.core.redis import RedisClient
        if await RedisClient.is_token_blacklisted(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )

    # Get user from database
    from bson import ObjectId
    user = await db.users.find_one({"_id": ObjectId(user_id)})

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return UserModel.serialize_user(user)


async def get_current_active_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Dependency to get the current active user.
    Can add additional checks here (e.g., email verification, account status).
    """
    # Add any additional checks here if needed
    # For example: if not current_user.get("is_active"):
    #     raise HTTPException(status_code=400, detail="Inactive user")

    return current_user
