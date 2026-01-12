"""
Celery tasks for GoalGetter background processing.
Includes email sending, meeting reminders, and maintenance tasks.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import asyncio

from celery import shared_task
from pymongo import MongoClient
from bson import ObjectId

from app.core.config import settings
from app.services.email_service import email_service

logger = logging.getLogger(__name__)


def get_sync_db():
    """
    Get synchronous MongoDB connection for Celery tasks.
    Celery tasks run in a separate process and need their own connection.
    """
    client = MongoClient(settings.MONGODB_URI)
    return client[settings.MONGODB_DB_NAME]


# Email Tasks

@shared_task(
    name="app.tasks.celery_tasks.send_email_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_email_task(
    self,
    email_type: str,
    to_email: str,
    user_name: str,
    **kwargs,
) -> Dict[str, Any]:
    """
    Generic email sending task.

    Args:
        email_type: Type of email ('welcome', 'meeting_invitation', 'meeting_reminder', 'milestone', 'phase_transition')
        to_email: Recipient email address
        user_name: Recipient's name
        **kwargs: Additional parameters specific to email type

    Returns:
        Dict with success status and message
    """
    try:
        logger.info(f"Sending {email_type} email to {to_email}")

        success = False

        if email_type == "welcome":
            success = email_service.send_welcome_email(to_email, user_name)

        elif email_type == "meeting_invitation":
            meeting_time = datetime.fromisoformat(kwargs.get("meeting_time"))
            duration = kwargs.get("duration_minutes", 30)
            success = email_service.send_meeting_invitation(
                to_email, user_name, meeting_time, duration
            )

        elif email_type == "meeting_reminder":
            meeting_time = datetime.fromisoformat(kwargs.get("meeting_time"))
            hours_until = kwargs.get("hours_until", 24)
            duration = kwargs.get("duration_minutes", 30)
            success = email_service.send_meeting_reminder(
                to_email, user_name, meeting_time, hours_until, duration
            )

        elif email_type == "milestone":
            goal_title = kwargs.get("goal_title", "")
            milestone = kwargs.get("milestone", "")
            success = email_service.send_goal_milestone_email(
                to_email, user_name, goal_title, milestone
            )

        elif email_type == "phase_transition":
            new_phase = kwargs.get("new_phase", "tracking")
            next_meeting = None
            if kwargs.get("next_meeting"):
                next_meeting = datetime.fromisoformat(kwargs.get("next_meeting"))
            success = email_service.send_phase_transition_email(
                to_email, user_name, new_phase, next_meeting
            )

        else:
            logger.warning(f"Unknown email type: {email_type}")
            return {"success": False, "message": f"Unknown email type: {email_type}"}

        return {
            "success": success,
            "message": f"{'Sent' if success else 'Failed to send'} {email_type} email to {to_email}",
        }

    except Exception as e:
        logger.error(f"Error sending {email_type} email to {to_email}: {e}")
        # Retry on failure
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            return {"success": False, "message": f"Max retries exceeded: {str(e)}"}


# Meeting Reminder Tasks

@shared_task(name="app.tasks.celery_tasks.send_meeting_reminders_task")
def send_meeting_reminders_task() -> Dict[str, Any]:
    """
    Check for upcoming meetings and send reminders.

    Sends reminders at:
    - 24 hours before meeting
    - 1 hour before meeting

    Returns:
        Dict with count of reminders sent
    """
    try:
        db = get_sync_db()
        current_time = datetime.utcnow()
        reminders_sent = 0

        # Find meetings needing 24-hour reminder
        # Look for meetings 23-25 hours away that haven't had 24h reminder
        window_24h_start = current_time + timedelta(hours=23)
        window_24h_end = current_time + timedelta(hours=25)

        meetings_24h = list(db.meetings.find({
            "status": "scheduled",
            "scheduled_at": {
                "$gte": window_24h_start,
                "$lte": window_24h_end,
            },
            "reminder_24h_sent": {"$ne": True},
        }))

        for meeting in meetings_24h:
            user = db.users.find_one({"_id": meeting["user_id"]})
            if user and user.get("settings", {}).get("email_notifications", True):
                # Queue email
                send_email_task.delay(
                    email_type="meeting_reminder",
                    to_email=user["email"],
                    user_name=user["name"],
                    meeting_time=meeting["scheduled_at"].isoformat(),
                    hours_until=24,
                    duration_minutes=meeting.get("duration_minutes", 30),
                )

                # Mark reminder as sent
                db.meetings.update_one(
                    {"_id": meeting["_id"]},
                    {"$set": {"reminder_24h_sent": True}}
                )
                reminders_sent += 1
                logger.info(f"Sent 24h reminder for meeting {meeting['_id']} to {user['email']}")

        # Find meetings needing 1-hour reminder
        window_1h_start = current_time + timedelta(minutes=50)
        window_1h_end = current_time + timedelta(minutes=70)

        meetings_1h = list(db.meetings.find({
            "status": "scheduled",
            "scheduled_at": {
                "$gte": window_1h_start,
                "$lte": window_1h_end,
            },
            "reminder_1h_sent": {"$ne": True},
        }))

        for meeting in meetings_1h:
            user = db.users.find_one({"_id": meeting["user_id"]})
            if user and user.get("settings", {}).get("email_notifications", True):
                # Queue email
                send_email_task.delay(
                    email_type="meeting_reminder",
                    to_email=user["email"],
                    user_name=user["name"],
                    meeting_time=meeting["scheduled_at"].isoformat(),
                    hours_until=1,
                    duration_minutes=meeting.get("duration_minutes", 30),
                )

                # Mark reminder as sent
                db.meetings.update_one(
                    {"_id": meeting["_id"]},
                    {"$set": {"reminder_1h_sent": True}}
                )
                reminders_sent += 1
                logger.info(f"Sent 1h reminder for meeting {meeting['_id']} to {user['email']}")

        logger.info(f"Meeting reminders task completed. Sent {reminders_sent} reminders.")
        return {"success": True, "reminders_sent": reminders_sent}

    except Exception as e:
        logger.error(f"Error in send_meeting_reminders_task: {e}")
        return {"success": False, "error": str(e)}


# Meeting Status Tasks

@shared_task(name="app.tasks.celery_tasks.update_meeting_statuses_task")
def update_meeting_statuses_task() -> Dict[str, Any]:
    """
    Update meeting statuses based on current time.

    - Mark meetings as 'active' when within window
    - Mark meetings as 'completed' when window has passed
    - Create next meeting for completed recurring meetings

    Returns:
        Dict with count of meetings updated
    """
    try:
        db = get_sync_db()
        current_time = datetime.utcnow()
        updated_count = 0
        next_meetings_created = 0

        window_before = timedelta(minutes=settings.MEETING_WINDOW_BEFORE_MINUTES)
        window_after = timedelta(minutes=settings.MEETING_WINDOW_AFTER_MINUTES)

        # Find scheduled meetings that should be active
        scheduled_meetings = list(db.meetings.find({"status": "scheduled"}))

        for meeting in scheduled_meetings:
            scheduled_at = meeting["scheduled_at"]
            duration_minutes = meeting.get("duration_minutes", 30)

            window_start = scheduled_at - window_before
            meeting_end = scheduled_at + timedelta(minutes=duration_minutes)
            window_end = meeting_end + window_after

            if window_start <= current_time <= window_end:
                # Should be active
                db.meetings.update_one(
                    {"_id": meeting["_id"]},
                    {"$set": {"status": "active"}}
                )
                updated_count += 1
                logger.info(f"Marked meeting {meeting['_id']} as active")

            elif current_time > window_end:
                # Window has passed - mark as completed
                db.meetings.update_one(
                    {"_id": meeting["_id"]},
                    {
                        "$set": {
                            "status": "completed",
                            "completed_at": window_end,
                        }
                    }
                )
                updated_count += 1
                logger.info(f"Marked meeting {meeting['_id']} as completed (auto)")

                # Create next meeting if user is in tracking phase
                next_meeting_created = create_next_meeting_for_user(db, meeting)
                if next_meeting_created:
                    next_meetings_created += 1

        # Find active meetings that should be completed
        active_meetings = list(db.meetings.find({"status": "active"}))

        for meeting in active_meetings:
            scheduled_at = meeting["scheduled_at"]
            duration_minutes = meeting.get("duration_minutes", 30)

            meeting_end = scheduled_at + timedelta(minutes=duration_minutes)
            window_end = meeting_end + window_after

            if current_time > window_end:
                db.meetings.update_one(
                    {"_id": meeting["_id"]},
                    {
                        "$set": {
                            "status": "completed",
                            "completed_at": window_end,
                        }
                    }
                )
                updated_count += 1
                logger.info(f"Marked meeting {meeting['_id']} as completed")

                # Create next meeting
                next_meeting_created = create_next_meeting_for_user(db, meeting)
                if next_meeting_created:
                    next_meetings_created += 1

        logger.info(
            f"Meeting status update completed. "
            f"Updated: {updated_count}, Next meetings created: {next_meetings_created}"
        )
        return {
            "success": True,
            "meetings_updated": updated_count,
            "next_meetings_created": next_meetings_created,
        }

    except Exception as e:
        logger.error(f"Error in update_meeting_statuses_task: {e}")
        return {"success": False, "error": str(e)}


def create_next_meeting_for_user(db, completed_meeting: Dict) -> bool:
    """
    Create the next meeting for a user after completing one.

    Args:
        db: MongoDB database instance
        completed_meeting: The meeting that was just completed

    Returns:
        bool: True if next meeting was created
    """
    try:
        user_id = completed_meeting["user_id"]
        user = db.users.find_one({"_id": user_id})

        if not user:
            return False

        # Only create next meeting if user is in tracking phase
        if user.get("phase") != "tracking":
            return False

        # Check if there's already a scheduled meeting
        existing = db.meetings.find_one({
            "user_id": user_id,
            "status": "scheduled",
            "scheduled_at": {"$gt": datetime.utcnow()},
        })

        if existing:
            logger.info(f"User {user_id} already has a scheduled meeting")
            return False

        # Calculate next meeting time
        interval_days = user.get("meeting_interval", settings.DEFAULT_MEETING_INTERVAL_DAYS)
        duration_minutes = user.get("settings", {}).get(
            "meeting_duration", settings.DEFAULT_MEETING_DURATION_MINUTES
        )

        last_meeting_time = completed_meeting["scheduled_at"]
        next_meeting_time = last_meeting_time + timedelta(days=interval_days)

        # If next meeting time is in the past, calculate from now
        if next_meeting_time < datetime.utcnow():
            next_meeting_time = datetime.utcnow() + timedelta(days=1)
            next_meeting_time = next_meeting_time.replace(
                hour=9, minute=0, second=0, microsecond=0
            )

        # Create meeting document
        meeting_doc = {
            "user_id": user_id,
            "scheduled_at": next_meeting_time,
            "duration_minutes": duration_minutes,
            "status": "scheduled",
            "calendar_event_id": None,
            "notes": None,
            "created_at": datetime.utcnow(),
            "completed_at": None,
        }

        result = db.meetings.insert_one(meeting_doc)
        logger.info(f"Created next meeting {result.inserted_id} for user {user_id} at {next_meeting_time}")

        # Send meeting invitation email
        if user.get("settings", {}).get("email_notifications", True):
            send_email_task.delay(
                email_type="meeting_invitation",
                to_email=user["email"],
                user_name=user["name"],
                meeting_time=next_meeting_time.isoformat(),
                duration_minutes=duration_minutes,
            )

        return True

    except Exception as e:
        logger.error(f"Error creating next meeting: {e}")
        return False


# Cleanup Tasks

@shared_task(name="app.tasks.celery_tasks.cleanup_old_messages_task")
def cleanup_old_messages_task(days_old: int = 90) -> Dict[str, Any]:
    """
    Clean up old chat messages to manage database size.

    Args:
        days_old: Delete messages older than this many days (default 90)

    Returns:
        Dict with count of messages deleted
    """
    try:
        db = get_sync_db()
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        # Only delete messages from completed meetings
        result = db.chat_messages.delete_many({
            "timestamp": {"$lt": cutoff_date},
            "meeting_id": {"$ne": None},  # Only delete meeting chat messages
        })

        deleted_count = result.deleted_count
        logger.info(f"Cleanup task deleted {deleted_count} old messages (older than {days_old} days)")

        return {"success": True, "deleted_count": deleted_count}

    except Exception as e:
        logger.error(f"Error in cleanup_old_messages_task: {e}")
        return {"success": False, "error": str(e)}


# Utility Tasks

@shared_task(name="app.tasks.celery_tasks.send_welcome_email_task")
def send_welcome_email_task(to_email: str, user_name: str) -> Dict[str, Any]:
    """
    Convenience task to send welcome email.

    Args:
        to_email: User's email
        user_name: User's name

    Returns:
        Dict with success status
    """
    return send_email_task(
        email_type="welcome",
        to_email=to_email,
        user_name=user_name,
    )


@shared_task(name="app.tasks.celery_tasks.send_phase_transition_email_task")
def send_phase_transition_email_task(
    to_email: str,
    user_name: str,
    new_phase: str,
    next_meeting: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convenience task to send phase transition email.

    Args:
        to_email: User's email
        user_name: User's name
        new_phase: New phase ('goal_setting' or 'tracking')
        next_meeting: Optional ISO format datetime of next meeting

    Returns:
        Dict with success status
    """
    return send_email_task(
        email_type="phase_transition",
        to_email=to_email,
        user_name=user_name,
        new_phase=new_phase,
        next_meeting=next_meeting,
    )


# Health Check Task

@shared_task(name="app.tasks.celery_tasks.health_check")
def health_check() -> Dict[str, Any]:
    """
    Simple health check task to verify Celery is working.

    Returns:
        Dict with status and timestamp
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Celery worker is operational",
    }
