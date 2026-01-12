"""
Meeting service handling meeting CRUD operations and business logic.
Includes meeting access control for the tracking phase.
"""
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
import math
import logging

from app.models.meeting import MeetingModel
from app.core.config import settings
from app.schemas.meeting import (
    MeetingCreate,
    MeetingSetup,
    MeetingUpdate,
    MeetingReschedule,
)

logger = logging.getLogger(__name__)


class MeetingService:
    """Service for meeting operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def create_meeting(
        self,
        user_id: str,
        meeting_data: MeetingCreate,
    ) -> Dict[str, Any]:
        """
        Create a new meeting for a user.
        """
        # Create meeting document
        meeting_doc = MeetingModel.create_meeting_document(
            user_id=user_id,
            scheduled_at=meeting_data.scheduled_at,
            duration_minutes=meeting_data.duration_minutes,
            notes=meeting_data.notes,
        )

        # Insert into database
        result = await self.db.meetings.insert_one(meeting_doc)
        meeting_doc["_id"] = result.inserted_id

        logger.info(f"Created meeting {result.inserted_id} for user {user_id}")

        return MeetingModel.serialize_meeting(meeting_doc)

    async def setup_recurring_meetings(
        self,
        user_id: str,
        setup_data: MeetingSetup,
    ) -> Dict[str, Any]:
        """
        Setup recurring meetings for a user entering tracking phase.
        Creates the first meeting based on the setup parameters.
        """
        # Update user's meeting interval
        await self.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "meeting_interval": setup_data.interval_days,
                    "settings.meeting_duration": setup_data.duration_minutes,
                    "updated_at": datetime.utcnow(),
                }
            }
        )

        # Calculate first meeting time
        if setup_data.first_meeting_at:
            first_meeting_time = setup_data.first_meeting_at
        else:
            first_meeting_time = MeetingModel.calculate_next_meeting_time(
                last_meeting=None,
                interval_days=setup_data.interval_days,
                meeting_time_hour=setup_data.preferred_hour,
                meeting_time_minute=setup_data.preferred_minute,
            )

        # Create first meeting
        meeting_doc = MeetingModel.create_meeting_document(
            user_id=user_id,
            scheduled_at=first_meeting_time,
            duration_minutes=setup_data.duration_minutes,
        )

        result = await self.db.meetings.insert_one(meeting_doc)
        meeting_doc["_id"] = result.inserted_id

        logger.info(f"Setup recurring meetings for user {user_id}, first meeting at {first_meeting_time}")

        return MeetingModel.serialize_meeting(meeting_doc)

    async def get_meeting_by_id(
        self,
        meeting_id: str,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a meeting by ID. Ensures user owns the meeting.
        """
        try:
            meeting = await self.db.meetings.find_one({
                "_id": ObjectId(meeting_id),
                "user_id": ObjectId(user_id),
            })
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid meeting ID format"
            )

        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting not found"
            )

        return MeetingModel.serialize_meeting(meeting)

    async def get_user_meetings(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        status_filter: Optional[str] = None,
        upcoming_only: bool = False,
        sort_by: str = "scheduled_at",
        sort_order: str = "asc",
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get paginated list of meetings for a user.
        """
        # Build query filter
        query: Dict[str, Any] = {"user_id": ObjectId(user_id)}

        if status_filter:
            query["status"] = status_filter

        if upcoming_only:
            query["scheduled_at"] = {"$gte": datetime.utcnow()}
            query["status"] = {"$in": ["scheduled", "active"]}

        # Calculate skip value
        skip = (page - 1) * page_size

        # Determine sort direction
        sort_direction = 1 if sort_order == "asc" else -1

        # Get total count
        total = await self.db.meetings.count_documents(query)

        # Get meetings with pagination and sorting
        cursor = self.db.meetings.find(query).sort(sort_by, sort_direction).skip(skip).limit(page_size)
        meetings = await cursor.to_list(length=page_size)

        return MeetingModel.serialize_meetings(meetings), total

    async def get_next_meeting(
        self,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get the next upcoming scheduled or active meeting for a user.
        """
        current_time = datetime.utcnow()

        # Find the next meeting that is either:
        # 1. Scheduled and in the future
        # 2. Active (meeting in progress)
        meeting = await self.db.meetings.find_one(
            {
                "user_id": ObjectId(user_id),
                "status": {"$in": ["scheduled", "active"]},
                "$or": [
                    {"scheduled_at": {"$gte": current_time}},
                    {"status": "active"},
                ],
            },
            sort=[("scheduled_at", 1)],
        )

        if meeting:
            return MeetingModel.serialize_meeting(meeting)

        return None

    async def get_active_meeting(
        self,
        user_id: str,
        current_time: Optional[datetime] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a meeting that is currently active or within its access window.

        A meeting is accessible if:
        1. Status is 'scheduled' or 'active'
        2. Current time is within the meeting window (30 min before to 90 min after start)
        """
        if current_time is None:
            current_time = datetime.utcnow()

        # Calculate the window boundaries
        window_before = timedelta(minutes=MeetingModel.WINDOW_BEFORE_MINUTES)
        window_after = timedelta(minutes=MeetingModel.WINDOW_AFTER_MINUTES)

        # Look for meetings where current time falls within the window
        # Window: scheduled_at - 30min <= current_time <= scheduled_at + duration + 60min
        meetings = await self.db.meetings.find(
            {
                "user_id": ObjectId(user_id),
                "status": {"$in": ["scheduled", "active"]},
            }
        ).to_list(length=10)

        for meeting in meetings:
            scheduled_at = meeting["scheduled_at"]
            duration_minutes = meeting.get("duration_minutes", 30)

            if MeetingModel.is_within_meeting_window(
                scheduled_at=scheduled_at,
                duration_minutes=duration_minutes,
                current_time=current_time,
            ):
                return MeetingModel.serialize_meeting(meeting)

        return None

    async def update_meeting(
        self,
        meeting_id: str,
        user_id: str,
        meeting_data: MeetingUpdate,
    ) -> Dict[str, Any]:
        """
        Update an existing meeting.
        """
        # Build update document
        update_doc = {}

        if meeting_data.scheduled_at is not None:
            update_doc["scheduled_at"] = meeting_data.scheduled_at

        if meeting_data.duration_minutes is not None:
            update_doc["duration_minutes"] = meeting_data.duration_minutes

        if meeting_data.notes is not None:
            update_doc["notes"] = meeting_data.notes

        if not update_doc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )

        try:
            result = await self.db.meetings.find_one_and_update(
                {
                    "_id": ObjectId(meeting_id),
                    "user_id": ObjectId(user_id),
                    "status": {"$in": ["scheduled", "active"]},  # Can only update non-completed meetings
                },
                {"$set": update_doc},
                return_document=True,
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid meeting ID format"
            )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting not found or cannot be updated"
            )

        return MeetingModel.serialize_meeting(result)

    async def reschedule_meeting(
        self,
        meeting_id: str,
        user_id: str,
        reschedule_data: MeetingReschedule,
    ) -> Dict[str, Any]:
        """
        Reschedule a meeting to a new time.
        """
        update_doc = {
            "scheduled_at": reschedule_data.scheduled_at,
        }

        if reschedule_data.notes is not None:
            update_doc["notes"] = reschedule_data.notes

        try:
            result = await self.db.meetings.find_one_and_update(
                {
                    "_id": ObjectId(meeting_id),
                    "user_id": ObjectId(user_id),
                    "status": {"$in": ["scheduled", "active"]},
                },
                {"$set": update_doc},
                return_document=True,
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid meeting ID format"
            )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting not found or cannot be rescheduled"
            )

        logger.info(f"Rescheduled meeting {meeting_id} to {reschedule_data.scheduled_at}")

        return MeetingModel.serialize_meeting(result)

    async def cancel_meeting(
        self,
        meeting_id: str,
        user_id: str,
    ) -> bool:
        """
        Cancel a meeting.
        """
        try:
            result = await self.db.meetings.find_one_and_update(
                {
                    "_id": ObjectId(meeting_id),
                    "user_id": ObjectId(user_id),
                    "status": {"$in": ["scheduled", "active"]},
                },
                {
                    "$set": {
                        "status": "cancelled",
                    }
                },
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid meeting ID format"
            )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting not found or cannot be cancelled"
            )

        logger.info(f"Cancelled meeting {meeting_id}")

        return True

    async def complete_meeting(
        self,
        meeting_id: str,
        user_id: str,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Mark a meeting as completed and create the next scheduled meeting.
        """
        # Get the meeting first
        try:
            meeting = await self.db.meetings.find_one({
                "_id": ObjectId(meeting_id),
                "user_id": ObjectId(user_id),
            })
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid meeting ID format"
            )

        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting not found"
            )

        if meeting["status"] not in ["scheduled", "active"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Meeting cannot be completed"
            )

        # Mark meeting as completed
        update_doc = {
            "status": "completed",
            "completed_at": datetime.utcnow(),
        }

        if notes is not None:
            update_doc["notes"] = notes

        result = await self.db.meetings.find_one_and_update(
            {"_id": ObjectId(meeting_id)},
            {"$set": update_doc},
            return_document=True,
        )

        # Get user to determine meeting interval
        user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        if user and user.get("phase") == "tracking":
            # Create next meeting
            interval_days = user.get("meeting_interval", settings.DEFAULT_MEETING_INTERVAL_DAYS)
            duration_minutes = user.get("settings", {}).get(
                "meeting_duration", settings.DEFAULT_MEETING_DURATION_MINUTES
            )

            next_meeting_time = MeetingModel.calculate_next_meeting_time(
                last_meeting=meeting["scheduled_at"],
                interval_days=interval_days,
            )

            next_meeting_doc = MeetingModel.create_meeting_document(
                user_id=user_id,
                scheduled_at=next_meeting_time,
                duration_minutes=duration_minutes,
            )

            await self.db.meetings.insert_one(next_meeting_doc)
            logger.info(f"Created next meeting for user {user_id} at {next_meeting_time}")

        logger.info(f"Completed meeting {meeting_id}")

        return MeetingModel.serialize_meeting(result)

    async def check_chat_access(
        self,
        user_id: str,
        current_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Check if a user can access the chat based on their phase and meeting status.

        Returns:
            dict: {
                "can_access": bool,
                "reason": str,
                "current_phase": str,
                "active_meeting": Optional[dict],
                "next_meeting": Optional[dict],
                "window_start": Optional[str],
                "window_end": Optional[str],
            }
        """
        if current_time is None:
            current_time = datetime.utcnow()

        # Get user
        user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        phase = user.get("phase", "goal_setting")

        # Goal setting phase - always allow access
        if phase == "goal_setting":
            return {
                "can_access": True,
                "reason": "Goal setting phase - unlimited access",
                "current_phase": phase,
                "active_meeting": None,
                "next_meeting": None,
                "window_start": None,
                "window_end": None,
            }

        # Tracking phase - check for active meeting window
        active_meeting = await self.get_active_meeting(user_id, current_time)

        if active_meeting:
            # Parse the scheduled_at to calculate window
            scheduled_at = datetime.fromisoformat(active_meeting["scheduled_at"].replace("Z", "+00:00"))
            duration_minutes = active_meeting.get("duration_minutes", 30)
            window_start, window_end = MeetingModel.get_meeting_window(
                scheduled_at, duration_minutes
            )

            return {
                "can_access": True,
                "reason": "Active meeting window",
                "current_phase": phase,
                "active_meeting": active_meeting,
                "next_meeting": None,
                "window_start": window_start.isoformat(),
                "window_end": window_end.isoformat(),
            }

        # No active meeting - find next meeting
        next_meeting = await self.get_next_meeting(user_id)

        return {
            "can_access": False,
            "reason": "No active meeting - chat access restricted to meeting windows",
            "current_phase": phase,
            "active_meeting": None,
            "next_meeting": next_meeting,
            "window_start": None,
            "window_end": None,
        }

    async def update_meeting_statuses(self) -> int:
        """
        Update meeting statuses based on current time.
        - Mark meetings as 'active' when within window
        - Mark meetings as 'completed' when window has passed

        This would typically be called by a background task.

        Returns:
            int: Number of meetings updated
        """
        current_time = datetime.utcnow()
        updated_count = 0

        # Find scheduled meetings that should be active
        scheduled_meetings = await self.db.meetings.find({
            "status": "scheduled"
        }).to_list(length=100)

        for meeting in scheduled_meetings:
            scheduled_at = meeting["scheduled_at"]
            duration_minutes = meeting.get("duration_minutes", 30)
            window_start, window_end = MeetingModel.get_meeting_window(
                scheduled_at, duration_minutes
            )

            if window_start <= current_time <= window_end:
                # Should be active
                await self.db.meetings.update_one(
                    {"_id": meeting["_id"]},
                    {"$set": {"status": "active"}}
                )
                updated_count += 1
            elif current_time > window_end:
                # Window has passed - mark as completed
                await self.db.meetings.update_one(
                    {"_id": meeting["_id"]},
                    {
                        "$set": {
                            "status": "completed",
                            "completed_at": window_end,
                        }
                    }
                )
                updated_count += 1

        # Find active meetings that should be completed
        active_meetings = await self.db.meetings.find({
            "status": "active"
        }).to_list(length=100)

        for meeting in active_meetings:
            scheduled_at = meeting["scheduled_at"]
            duration_minutes = meeting.get("duration_minutes", 30)
            _, window_end = MeetingModel.get_meeting_window(
                scheduled_at, duration_minutes
            )

            if current_time > window_end:
                await self.db.meetings.update_one(
                    {"_id": meeting["_id"]},
                    {
                        "$set": {
                            "status": "completed",
                            "completed_at": window_end,
                        }
                    }
                )
                updated_count += 1

        if updated_count > 0:
            logger.info(f"Updated {updated_count} meeting statuses")

        return updated_count

    async def create_first_meeting_for_user(
        self,
        user_id: str,
        interval_days: Optional[int] = None,
        duration_minutes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Create the first meeting when a user transitions to tracking phase.
        """
        # Get user settings
        user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        if interval_days is None:
            interval_days = user.get("meeting_interval", settings.DEFAULT_MEETING_INTERVAL_DAYS)

        if duration_minutes is None:
            duration_minutes = user.get("settings", {}).get(
                "meeting_duration", settings.DEFAULT_MEETING_DURATION_MINUTES
            )

        # Calculate first meeting time
        first_meeting_time = MeetingModel.calculate_next_meeting_time(
            last_meeting=None,
            interval_days=interval_days,
        )

        # Create meeting
        meeting_doc = MeetingModel.create_meeting_document(
            user_id=user_id,
            scheduled_at=first_meeting_time,
            duration_minutes=duration_minutes,
        )

        result = await self.db.meetings.insert_one(meeting_doc)
        meeting_doc["_id"] = result.inserted_id

        logger.info(f"Created first meeting for user {user_id} at {first_meeting_time}")

        return MeetingModel.serialize_meeting(meeting_doc)
