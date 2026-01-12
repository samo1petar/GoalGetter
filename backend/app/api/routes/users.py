"""
Users API endpoints.
Handles user profile management and phase transitions.
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Response
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.core.database import get_database
from app.core.security import get_current_active_user
from app.core.config import settings
from app.models.user import UserModel
from app.services.meeting_service import MeetingService
from app.schemas.user import (
    UserResponse,
    UserUpdate,
    UserPhaseUpdate,
    UserSettings,
)
from app.schemas.meeting import MeetingSetup, MeetingResponse

router = APIRouter()


class UserService:
    """Service for user operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def get_user_by_id(self, user_id: str) -> dict:
        """Get user by ID."""
        try:
            user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format"
            )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return UserModel.serialize_user(user)

    async def update_user(
        self,
        user_id: str,
        update_data: UserUpdate,
    ) -> dict:
        """Update user profile."""
        update_doc = {"updated_at": datetime.utcnow()}

        if update_data.name is not None:
            update_doc["name"] = update_data.name

        if update_data.settings is not None:
            # Update individual settings fields
            settings_dict = update_data.settings.model_dump(exclude_unset=True)
            for key, value in settings_dict.items():
                update_doc[f"settings.{key}"] = value

        try:
            result = await self.db.users.find_one_and_update(
                {"_id": ObjectId(user_id)},
                {"$set": update_doc},
                return_document=True,
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format"
            )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return UserModel.serialize_user(result)

    async def transition_to_tracking(
        self,
        user_id: str,
        meeting_setup: Optional[MeetingSetup] = None,
    ) -> dict:
        """
        Transition user from goal_setting phase to tracking phase.
        Creates the first meeting based on meeting configuration.
        """
        # Get current user
        user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Check current phase
        if user.get("phase") == "tracking":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already in tracking phase"
            )

        # Update user phase
        update_doc = {
            "phase": "tracking",
            "updated_at": datetime.utcnow(),
        }

        # Update meeting interval if provided
        if meeting_setup:
            update_doc["meeting_interval"] = meeting_setup.interval_days
            update_doc["settings.meeting_duration"] = meeting_setup.duration_minutes

        await self.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_doc}
        )

        # Create first meeting
        meeting_service = MeetingService(self.db)

        if meeting_setup:
            first_meeting = await meeting_service.setup_recurring_meetings(
                user_id=user_id,
                setup_data=meeting_setup,
            )
        else:
            # Use default settings
            first_meeting = await meeting_service.create_first_meeting_for_user(
                user_id=user_id,
            )

        # Get updated user
        updated_user = await self.db.users.find_one({"_id": ObjectId(user_id)})

        return {
            "user": UserModel.serialize_user(updated_user),
            "first_meeting": first_meeting,
            "message": "Successfully transitioned to tracking phase",
        }

    async def delete_user(self, user_id: str) -> bool:
        """Delete user and all associated data."""
        try:
            # Delete user's meetings
            await self.db.meetings.delete_many({"user_id": ObjectId(user_id)})

            # Delete user's goals
            await self.db.goals.delete_many({"user_id": ObjectId(user_id)})

            # Delete user's chat messages
            await self.db.chat_messages.delete_many({"user_id": ObjectId(user_id)})

            # Delete user
            result = await self.db.users.delete_one({"_id": ObjectId(user_id)})

        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format"
            )

        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return True


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Get the current user's profile.

    Returns the full user profile including settings.
    """
    user_service = UserService(db)
    user = await user_service.get_user_by_id(current_user["id"])
    return user


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    update_data: UserUpdate,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Update the current user's profile.

    - **name**: New display name (optional)
    - **settings**: Updated settings (optional)
      - **meeting_duration**: Meeting duration in minutes
      - **timezone**: User's timezone
      - **email_notifications**: Enable/disable email notifications

    Returns the updated user profile.
    """
    user_service = UserService(db)
    user = await user_service.update_user(
        user_id=current_user["id"],
        update_data=update_data,
    )
    return user


class PhaseTransitionRequest(UserPhaseUpdate):
    """Extended schema for phase transition with meeting setup."""
    meeting_setup: Optional[MeetingSetup] = None


class PhaseTransitionResponse(UserResponse):
    """Response for phase transition."""
    first_meeting: Optional[MeetingResponse] = None
    message: str = ""


@router.patch("/me/phase")
async def transition_user_phase(
    phase_data: PhaseTransitionRequest,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Transition the user to a new phase.

    When transitioning to "tracking" phase:
    - Creates the first scheduled meeting
    - Optionally configures recurring meeting schedule

    - **phase**: New phase ("goal_setting" or "tracking")
    - **meeting_setup**: Optional meeting configuration for tracking phase
      - **interval_days**: Days between meetings (1-90)
      - **duration_minutes**: Meeting duration in minutes
      - **preferred_hour**: Preferred meeting hour (UTC)
      - **preferred_minute**: Preferred meeting minute

    Returns the updated user profile and first meeting (if transitioning to tracking).
    """
    user_service = UserService(db)

    if phase_data.phase == "tracking":
        # Transition to tracking phase
        result = await user_service.transition_to_tracking(
            user_id=current_user["id"],
            meeting_setup=phase_data.meeting_setup,
        )
        return result

    elif phase_data.phase == "goal_setting":
        # Transition back to goal_setting (if allowed)
        try:
            await db.users.update_one(
                {"_id": ObjectId(current_user["id"])},
                {
                    "$set": {
                        "phase": "goal_setting",
                        "updated_at": datetime.utcnow(),
                    }
                }
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update phase"
            )

        user = await user_service.get_user_by_id(current_user["id"])
        return {
            "user": user,
            "first_meeting": None,
            "message": "Successfully transitioned to goal_setting phase",
        }

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid phase. Must be 'goal_setting' or 'tracking'"
        )


@router.get("/me/phase")
async def get_current_phase(
    current_user: dict = Depends(get_current_active_user),
):
    """
    Get the current user's phase.

    Returns the current phase and related information.
    """
    return {
        "phase": current_user.get("phase", "goal_setting"),
        "meeting_interval": current_user.get("meeting_interval", settings.DEFAULT_MEETING_INTERVAL_DAYS),
        "calendar_connected": current_user.get("calendar_connected", False),
    }


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Delete the current user's account.

    This will permanently delete:
    - User account
    - All goals
    - All meetings
    - All chat messages

    This action cannot be undone.

    Returns 204 No Content on success.
    """
    user_service = UserService(db)
    await user_service.delete_user(current_user["id"])
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me/settings")
async def get_user_settings(
    current_user: dict = Depends(get_current_active_user),
):
    """
    Get the current user's settings.

    Returns user settings including meeting preferences and notification settings.
    """
    return {
        "meeting_duration": current_user.get("settings", {}).get(
            "meeting_duration", settings.DEFAULT_MEETING_DURATION_MINUTES
        ),
        "timezone": current_user.get("settings", {}).get("timezone", "UTC"),
        "email_notifications": current_user.get("settings", {}).get("email_notifications", True),
        "meeting_interval": current_user.get("meeting_interval", settings.DEFAULT_MEETING_INTERVAL_DAYS),
    }


@router.put("/me/settings")
async def update_user_settings(
    settings_data: UserSettings,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Update the current user's settings.

    - **meeting_duration**: Meeting duration in minutes
    - **timezone**: User's timezone
    - **email_notifications**: Enable/disable email notifications

    Returns the updated settings.
    """
    update_data = UserUpdate(settings=settings_data)
    user_service = UserService(db)
    user = await user_service.update_user(
        user_id=current_user["id"],
        update_data=update_data,
    )
    return user.get("settings", {})
