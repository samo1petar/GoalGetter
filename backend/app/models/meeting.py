"""
Meeting model for MongoDB.
Represents scheduled coaching meetings between users and the AI coach.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from bson import ObjectId

from app.core.config import settings


class MeetingModel:
    """
    Meeting model representing a meeting document in the database.
    This is a dict-based model for MongoDB documents.
    """

    VALID_STATUSES = ["scheduled", "active", "completed", "cancelled"]

    # Meeting window constants
    WINDOW_BEFORE_MINUTES = settings.MEETING_WINDOW_BEFORE_MINUTES
    WINDOW_AFTER_MINUTES = settings.MEETING_WINDOW_AFTER_MINUTES

    @staticmethod
    def create_meeting_document(
        user_id: str,
        scheduled_at: datetime,
        duration_minutes: int = 30,
        status: str = "scheduled",
        calendar_event_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> dict:
        """Create a new meeting document for MongoDB."""
        if status not in MeetingModel.VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}. Must be one of {MeetingModel.VALID_STATUSES}")

        return {
            "user_id": ObjectId(user_id),
            "scheduled_at": scheduled_at,
            "duration_minutes": duration_minutes,
            "status": status,
            "calendar_event_id": calendar_event_id,
            "notes": notes,
            "created_at": datetime.utcnow(),
            "completed_at": None,
        }

    @staticmethod
    def serialize_meeting(meeting_doc: dict) -> Optional[dict]:
        """Serialize meeting document for API response."""
        if not meeting_doc:
            return None

        scheduled_at = meeting_doc["scheduled_at"]
        if isinstance(scheduled_at, datetime):
            scheduled_at_str = scheduled_at.isoformat()
        else:
            scheduled_at_str = scheduled_at

        created_at = meeting_doc.get("created_at")
        if isinstance(created_at, datetime):
            created_at_str = created_at.isoformat()
        else:
            created_at_str = created_at

        completed_at = meeting_doc.get("completed_at")
        if isinstance(completed_at, datetime):
            completed_at_str = completed_at.isoformat()
        else:
            completed_at_str = completed_at

        return {
            "id": str(meeting_doc["_id"]),
            "user_id": str(meeting_doc["user_id"]),
            "scheduled_at": scheduled_at_str,
            "duration_minutes": meeting_doc.get("duration_minutes", 30),
            "status": meeting_doc["status"],
            "calendar_event_id": meeting_doc.get("calendar_event_id"),
            "notes": meeting_doc.get("notes"),
            "created_at": created_at_str,
            "completed_at": completed_at_str,
        }

    @staticmethod
    def serialize_meetings(meetings: List[dict]) -> List[dict]:
        """Serialize multiple meeting documents for API response."""
        return [MeetingModel.serialize_meeting(meeting) for meeting in meetings if meeting]

    @staticmethod
    def get_meeting_window(scheduled_at: datetime, duration_minutes: int = 30) -> tuple:
        """
        Get the meeting access window.

        Meeting window starts WINDOW_BEFORE_MINUTES before scheduled time
        and ends WINDOW_AFTER_MINUTES after the meeting end time.

        Returns:
            tuple: (window_start, window_end) as datetime objects
        """
        window_start = scheduled_at - timedelta(minutes=MeetingModel.WINDOW_BEFORE_MINUTES)
        meeting_end = scheduled_at + timedelta(minutes=duration_minutes)
        window_end = meeting_end + timedelta(minutes=MeetingModel.WINDOW_AFTER_MINUTES)

        return window_start, window_end

    @staticmethod
    def is_within_meeting_window(
        scheduled_at: datetime,
        duration_minutes: int,
        current_time: Optional[datetime] = None
    ) -> bool:
        """
        Check if current time is within the meeting window.

        Args:
            scheduled_at: The scheduled meeting start time
            duration_minutes: Meeting duration in minutes
            current_time: Optional current time (defaults to now)

        Returns:
            bool: True if within meeting window
        """
        if current_time is None:
            current_time = datetime.utcnow()

        window_start, window_end = MeetingModel.get_meeting_window(
            scheduled_at, duration_minutes
        )

        return window_start <= current_time <= window_end

    @staticmethod
    def calculate_next_meeting_time(
        last_meeting: Optional[datetime],
        interval_days: int,
        meeting_time_hour: int = 9,
        meeting_time_minute: int = 0,
    ) -> datetime:
        """
        Calculate the next meeting time based on interval.

        Args:
            last_meeting: Last meeting datetime or None for first meeting
            interval_days: Days between meetings
            meeting_time_hour: Hour for meeting (default 9 AM)
            meeting_time_minute: Minute for meeting (default 0)

        Returns:
            datetime: Next meeting scheduled time
        """
        if last_meeting is None:
            # First meeting - schedule for next occurrence of the preferred time
            now = datetime.utcnow()
            next_meeting = now.replace(
                hour=meeting_time_hour,
                minute=meeting_time_minute,
                second=0,
                microsecond=0
            )

            # If the time has already passed today, schedule for tomorrow
            if next_meeting <= now:
                next_meeting += timedelta(days=1)

            return next_meeting

        # Calculate next meeting from last meeting
        next_meeting = last_meeting + timedelta(days=interval_days)
        next_meeting = next_meeting.replace(
            hour=meeting_time_hour,
            minute=meeting_time_minute,
            second=0,
            microsecond=0
        )

        return next_meeting
