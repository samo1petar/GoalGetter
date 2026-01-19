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

        # Store state in Redis with 10-minute expiration for validation
        from app.core.redis import RedisClient
        await RedisClient.set_cache(
            f"oauth_state:{state}",
            "valid",
            ttl=600  # 10 minutes
        )

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

        # Validate state from Redis to prevent CSRF
        if state:
            from app.core.redis import RedisClient
            stored_state = await RedisClient.get_cache(f"oauth_state:{state}")
            if not stored_state:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired OAuth state"
                )
            # Delete state after use (one-time use)
            await RedisClient.delete_cache(f"oauth_state:{state}")

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

    async def request_password_reset(self, email: str) -> bool:
        """
        Generate password reset token and send email.
        Returns True regardless of whether user exists (prevents email enumeration).
        """
        user = await self.db.users.find_one({"email": email.lower()})

        if not user:
            # Don't reveal if user exists - return success anyway
            return True

        # Only allow reset for email-authenticated users
        if user.get("auth_provider") != "email":
            # User uses OAuth - can't reset password
            return True

        # Generate secure token
        reset_token = secrets.token_urlsafe(32)

        # Store in Redis with 1-hour expiry
        from app.core.redis import RedisClient
        await RedisClient.set_cache(
            f"password_reset:{reset_token}",
            str(user["_id"]),
            ttl=3600  # 1 hour
        )

        # Send email
        from app.services.email_service import email_service
        email_service.send_password_reset_email(
            to_email=email,
            user_name=user.get("name", "User"),
            reset_token=reset_token
        )

        return True

    async def confirm_password_reset(self, token: str, new_password: str) -> bool:
        """
        Validate reset token and update password.
        """
        from app.core.redis import RedisClient
        from bson import ObjectId

        user_id = await RedisClient.get_cache(f"password_reset:{token}")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )

        # Update password
        hashed_password = SecurityUtils.get_password_hash(new_password)

        result = await self.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "hashed_password": hashed_password,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        # Delete used token
        await RedisClient.delete_cache(f"password_reset:{token}")

        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return True

    async def setup_2fa(self, user_id: str) -> dict:
        """Generate 2FA secret and QR code URI."""
        import pyotp
        from bson import ObjectId

        user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.get("two_factor_enabled"):
            raise HTTPException(status_code=400, detail="2FA is already enabled")

        # Generate secret
        secret = pyotp.random_base32()

        # Store secret (not enabled yet)
        await self.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"two_factor_secret": secret}}
        )

        # Generate QR code URI
        totp = pyotp.TOTP(secret)
        qr_uri = totp.provisioning_uri(
            name=user["email"],
            issuer_name=settings.APP_NAME
        )

        # Generate backup codes
        backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]

        # Store backup codes (hashed)
        hashed_codes = [SecurityUtils.get_password_hash(code) for code in backup_codes]
        await self.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"two_factor_backup_codes": hashed_codes}}
        )

        return {
            "secret": secret,
            "qr_code_uri": qr_uri,
            "backup_codes": backup_codes
        }

    async def verify_and_enable_2fa(self, user_id: str, code: str) -> bool:
        """Verify TOTP code and enable 2FA."""
        import pyotp
        from bson import ObjectId

        user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        if not user or not user.get("two_factor_secret"):
            raise HTTPException(status_code=400, detail="2FA setup not initiated")

        totp = pyotp.TOTP(user["two_factor_secret"])
        if not totp.verify(code):
            raise HTTPException(status_code=400, detail="Invalid verification code")

        await self.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "two_factor_enabled": True,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        return True

    async def disable_2fa(self, user_id: str, code: str) -> bool:
        """Disable 2FA after code verification."""
        import pyotp
        from bson import ObjectId

        user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        if not user or not user.get("two_factor_enabled"):
            raise HTTPException(status_code=400, detail="2FA is not enabled")

        # Verify the code first
        totp = pyotp.TOTP(user["two_factor_secret"])
        code_valid = totp.verify(code)

        # If TOTP code is invalid, check if it's a backup code
        if not code_valid:
            code_valid = self._verify_backup_code(user, code)

        if not code_valid:
            raise HTTPException(status_code=400, detail="Invalid verification code")

        await self.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "two_factor_enabled": False,
                    "two_factor_secret": None,
                    "two_factor_backup_codes": None,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        return True

    def _verify_backup_code(self, user: dict, code: str) -> bool:
        """Verify a backup code and remove it if valid."""
        backup_codes = user.get("two_factor_backup_codes", [])
        for stored_hash in backup_codes:
            if SecurityUtils.verify_password(code.upper(), stored_hash):
                return True
        return False

    async def login_user_with_2fa(self, login_data, totp_code: str = None) -> dict:
        """
        Authenticate user with optional 2FA support.
        Returns requires_2fa: true if 2FA is enabled but code not provided.
        """
        import pyotp

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

        # Check if 2FA is enabled
        if user.get("two_factor_enabled"):
            if not totp_code:
                # Return indicator that 2FA is required
                return {
                    "requires_2fa": True,
                    "message": "Two-factor authentication required"
                }

            # Verify TOTP code
            totp = pyotp.TOTP(user["two_factor_secret"])
            if not totp.verify(totp_code):
                # Check backup codes
                if not self._verify_backup_code(user, totp_code):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid 2FA code"
                    )
                # If backup code was used, remove it from the list
                backup_codes = user.get("two_factor_backup_codes", [])
                new_backup_codes = [
                    bc for bc in backup_codes
                    if not SecurityUtils.verify_password(totp_code.upper(), bc)
                ]
                await self.db.users.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"two_factor_backup_codes": new_backup_codes}}
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
