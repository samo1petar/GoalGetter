"""
Authentication service handling user registration, login, and OAuth.
"""
from typing import Optional, Dict, Any
from datetime import datetime
import secrets
import httpx
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings
from app.core.security import SecurityUtils
from app.models.user import UserModel
from app.schemas.user import UserCreate, LoginRequest


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def register_user(self, user_data: UserCreate) -> Dict[str, Any]:
        """
        Register a new user with email and password.
        """
        # Check if user already exists
        existing_user = await self.db.users.find_one({"email": user_data.email.lower()})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Hash password
        hashed_password = SecurityUtils.get_password_hash(user_data.password)

        # Create user document
        user_doc = UserModel.create_user_document(
            email=user_data.email,
            name=user_data.name,
            auth_provider="email",
            auth_provider_id=user_data.email.lower(),
            hashed_password=hashed_password
        )

        # Insert into database
        result = await self.db.users.insert_one(user_doc)
        user_doc["_id"] = result.inserted_id

        # Generate tokens
        tokens = SecurityUtils.create_token_pair(
            user_id=str(result.inserted_id),
            email=user_data.email
        )

        # Serialize user
        user_response = UserModel.serialize_user(user_doc)

        return {
            **tokens,
            "user": user_response
        }

    async def login_user(self, login_data: LoginRequest) -> Dict[str, Any]:
        """
        Authenticate user with email and password.
        """
        # Find user by email
        user = await self.db.users.find_one({"email": login_data.email.lower()})

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )

        # Verify password (only for email auth)
        if user["auth_provider"] != "email":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"This account uses {user['auth_provider']} authentication"
            )

        if not user.get("hashed_password"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Account configuration error"
            )

        if not SecurityUtils.verify_password(login_data.password, user["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )

        # Generate tokens
        tokens = SecurityUtils.create_token_pair(
            user_id=str(user["_id"]),
            email=user["email"]
        )

        # Serialize user
        user_response = UserModel.serialize_user(user)

        return {
            **tokens,
            "user": user_response
        }

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, str]:
        """
        Generate a new access token from a refresh token.
        """
        # Verify refresh token
        payload = SecurityUtils.verify_token(refresh_token, token_type="refresh")
        user_id = payload.get("user_id")
        email = payload.get("email")

        if not user_id or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        # Verify user still exists
        from bson import ObjectId
        user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        # Create new access token
        access_token = SecurityUtils.create_access_token(
            {"user_id": user_id, "email": email}
        )

        return {
            "access_token": access_token,
            "token_type": "bearer"
        }

    async def google_oauth_url(self, redirect_uri: Optional[str] = None) -> str:
        """
        Generate Google OAuth authorization URL.
        """
        if not settings.GOOGLE_CLIENT_ID:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Google OAuth not configured"
            )

        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)

        # TODO: Store state in Redis with expiration for validation

        redirect_uri = redirect_uri or settings.GOOGLE_REDIRECT_URI

        # Google OAuth URL
        auth_url = (
            "https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={settings.GOOGLE_CLIENT_ID}&"
            f"redirect_uri={redirect_uri}&"
            "response_type=code&"
            "scope=openid email profile&"
            f"state={state}&"
            "access_type=offline&"
            "prompt=consent"
        )

        return auth_url

    async def google_oauth_callback(self, code: str, state: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle Google OAuth callback and create/login user.
        """
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Google OAuth not configured"
            )

        # TODO: Validate state from Redis

        # Exchange code for tokens
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code"
        }

        async with httpx.AsyncClient() as client:
            token_response = await client.post(token_url, data=token_data)

            if token_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to exchange code for tokens"
                )

            tokens = token_response.json()
            access_token = tokens.get("access_token")

            # Get user info from Google
            userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
            headers = {"Authorization": f"Bearer {access_token}"}
            userinfo_response = await client.get(userinfo_url, headers=headers)

            if userinfo_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get user info from Google"
                )

            user_info = userinfo_response.json()

        # Check if user exists
        google_id = user_info["id"]
        email = user_info["email"]
        name = user_info.get("name", email.split("@")[0])
        profile_image = user_info.get("picture")

        existing_user = await self.db.users.find_one({
            "$or": [
                {"auth_provider_id": google_id, "auth_provider": "google"},
                {"email": email.lower()}
            ]
        })

        if existing_user:
            # Update user info if needed
            update_data = {
                "updated_at": datetime.utcnow(),
                "auth_provider": "google",
                "auth_provider_id": google_id
            }
            if profile_image:
                update_data["profile_image"] = profile_image

            await self.db.users.update_one(
                {"_id": existing_user["_id"]},
                {"$set": update_data}
            )

            user_id = str(existing_user["_id"])
        else:
            # Create new user
            user_doc = UserModel.create_user_document(
                email=email,
                name=name,
                auth_provider="google",
                auth_provider_id=google_id,
                profile_image=profile_image
            )

            result = await self.db.users.insert_one(user_doc)
            user_id = str(result.inserted_id)
            user_doc["_id"] = result.inserted_id
            existing_user = user_doc

        # Generate JWT tokens
        auth_tokens = SecurityUtils.create_token_pair(
            user_id=user_id,
            email=email
        )

        # Get updated user
        user = await self.db.users.find_one({"_id": existing_user["_id"]})
        user_response = UserModel.serialize_user(user)

        return {
            **auth_tokens,
            "user": user_response
        }
