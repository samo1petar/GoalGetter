"""
User model for MongoDB.
"""
from datetime import datetime
from typing import Optional
from bson import ObjectId


class UserModel:
    """
    User model representing a user in the database.
    This is a simple dict-based model for MongoDB documents.
    """

    @staticmethod
    def create_user_document(
        email: str,
        name: str,
        auth_provider: str,
        auth_provider_id: str,
        profile_image: Optional[str] = None,
        hashed_password: Optional[str] = None,
    ) -> dict:
        """Create a new user document for MongoDB."""
        return {
            "email": email.lower(),
            "name": name,
            "auth_provider": auth_provider,  # "google", "email", etc.
            "auth_provider_id": auth_provider_id,
            "profile_image": profile_image,
            "hashed_password": hashed_password,  # Only for email/password auth
            "phase": "goal_setting",  # Start in goal_setting phase
            "meeting_interval": 7,  # Default: weekly meetings
            "calendar_connected": False,
            "calendar_access_token": None,
            "calendar_refresh_token": None,
            # Two-factor authentication
            "two_factor_enabled": False,
            "two_factor_secret": None,
            "two_factor_backup_codes": None,
            # LLM provider preference
            "llm_provider": "claude",  # Default to Claude
            # SECURITY: Token version for invalidating all tokens on password change
            # Increment this value when password is reset to invalidate existing refresh tokens
            "token_version": 1,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "settings": {
                "meeting_duration": 30,  # minutes
                "timezone": "UTC",
                "email_notifications": True,
            }
        }

    @staticmethod
    def serialize_user(user_doc: dict) -> dict:
        """Serialize user document for API response."""
        if not user_doc:
            return None

        return {
            "id": str(user_doc["_id"]),
            "email": user_doc["email"],
            "name": user_doc["name"],
            "auth_provider": user_doc["auth_provider"],
            "profile_image": user_doc.get("profile_image"),
            "phase": user_doc["phase"],
            "meeting_interval": user_doc["meeting_interval"],
            "calendar_connected": user_doc.get("calendar_connected", False),
            "two_factor_enabled": user_doc.get("two_factor_enabled", False),
            "llm_provider": user_doc.get("llm_provider", "claude"),
            "created_at": user_doc["created_at"].isoformat(),
            "updated_at": user_doc["updated_at"].isoformat(),
            "settings": user_doc.get("settings", {}),
        }


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")
