"""
Meetings API endpoints.
Handles meeting scheduling, management, and access control.
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from motor.motor_asyncio import AsyncIOMotorDatabase
import math

from app.core.database import get_database
from app.core.security import get_current_active_user
from app.core.config import settings
from app.services.meeting_service import MeetingService
from app.services.calendar_service import calendar_service
from app.schemas.meeting import (
    MeetingCreate,
    MeetingSetup,
    MeetingUpdate,
    MeetingReschedule,
    MeetingComplete,
    MeetingResponse,
    MeetingListResponse,
    MeetingAccessResponse,
    NextMeetingResponse,
)

router = APIRouter()


@router.post("/setup", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def setup_meetings(
    setup_data: MeetingSetup,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Setup recurring meetings for the user.

    This endpoint configures the meeting schedule and creates the first meeting.
    Typically called when a user transitions from goal_setting to tracking phase.

    - **interval_days**: Days between meetings (1-90)
    - **first_meeting_at**: Optional specific time for first meeting
    - **duration_minutes**: Meeting duration in minutes (15-180)
    - **preferred_hour**: Preferred hour for meetings (0-23, UTC)
    - **preferred_minute**: Preferred minute for meetings (0-59)

    Returns the created first meeting.
    """
    meeting_service = MeetingService(db)
    meeting = await meeting_service.setup_recurring_meetings(
        user_id=current_user["id"],
        setup_data=setup_data,
    )
    return meeting


@router.post("", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    meeting_data: MeetingCreate,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Create a new meeting.

    - **scheduled_at**: Meeting start time (datetime)
    - **duration_minutes**: Meeting duration in minutes (default: 30)
    - **notes**: Optional notes for the meeting

    Returns the created meeting.
    """
    meeting_service = MeetingService(db)
    meeting = await meeting_service.create_meeting(
        user_id=current_user["id"],
        meeting_data=meeting_data,
    )
    return meeting


@router.get("", response_model=MeetingListResponse)
async def list_meetings(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(
        default=None,
        alias="status",
        pattern="^(scheduled|active|completed|cancelled)$",
        description="Filter by status"
    ),
    upcoming_only: bool = Query(
        default=False,
        description="Only show upcoming meetings"
    ),
    sort_by: str = Query(
        default="scheduled_at",
        pattern="^(scheduled_at|created_at)$",
        description="Sort field"
    ),
    sort_order: str = Query(
        default="asc",
        pattern="^(asc|desc)$",
        description="Sort order"
    ),
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    List all meetings for the current user.

    Supports pagination, filtering, and sorting.

    - **page**: Page number (default: 1)
    - **page_size**: Number of items per page (default: 20, max: 100)
    - **status**: Filter by meeting status
    - **upcoming_only**: Only show scheduled/active meetings in the future
    - **sort_by**: Sort by field (scheduled_at, created_at)
    - **sort_order**: Sort order (asc, desc)

    Returns paginated list of meetings.
    """
    meeting_service = MeetingService(db)

    meetings, total = await meeting_service.get_user_meetings(
        user_id=current_user["id"],
        page=page,
        page_size=page_size,
        status_filter=status_filter,
        upcoming_only=upcoming_only,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return MeetingListResponse(
        meetings=meetings,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/next", response_model=NextMeetingResponse)
async def get_next_meeting(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Get the next scheduled or active meeting.

    Returns the next meeting with additional information about chat access.
    """
    meeting_service = MeetingService(db)

    # Check for active meeting first
    active_meeting = await meeting_service.get_active_meeting(current_user["id"])

    if active_meeting:
        return NextMeetingResponse(
            meeting=active_meeting,
            message="Meeting is currently active",
            can_access_now=True,
            countdown_seconds=None,
        )

    # Get next scheduled meeting
    next_meeting = await meeting_service.get_next_meeting(current_user["id"])

    if next_meeting:
        # Calculate countdown
        scheduled_at = datetime.fromisoformat(next_meeting["scheduled_at"].replace("Z", "+00:00"))
        now = datetime.utcnow()
        countdown = int((scheduled_at - now).total_seconds())

        return NextMeetingResponse(
            meeting=next_meeting,
            message="Next meeting is scheduled",
            can_access_now=countdown <= settings.MEETING_WINDOW_BEFORE_MINUTES * 60,
            countdown_seconds=max(countdown, 0),
        )

    return NextMeetingResponse(
        meeting=None,
        message="No upcoming meetings scheduled",
        can_access_now=False,
        countdown_seconds=None,
    )


@router.get("/access", response_model=MeetingAccessResponse)
async def check_meeting_access(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Check if the user can currently access the chat.

    In goal_setting phase, access is always granted.
    In tracking phase, access is only granted during meeting windows
    (30 minutes before to 60 minutes after meeting end).

    Returns access status and relevant meeting information.
    """
    meeting_service = MeetingService(db)

    access_info = await meeting_service.check_chat_access(user_id=current_user["id"])

    return MeetingAccessResponse(**access_info)


@router.get("/calendar/status")
async def get_calendar_status(
    current_user: dict = Depends(get_current_active_user),
):
    """
    Get the status of Google Calendar integration.

    Returns whether calendar sync is enabled and available features.
    """
    return calendar_service.get_calendar_status()


@router.get("/email/status")
async def get_email_status(
    current_user: dict = Depends(get_current_active_user),
):
    """
    Get the status of email service configuration.

    Returns whether email sending is properly configured.
    """
    from app.services.email_service import get_email_service
    from app.core.config import settings

    email_service = get_email_service()
    return {
        "is_configured": email_service.is_configured,
        "from_email": settings.FROM_EMAIL,
        "from_name": settings.FROM_NAME,
        "message": "Email service is ready" if email_service.is_configured else "SENDGRID_API_KEY not set - emails will not be sent"
    }


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(
    meeting_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Get a specific meeting by ID.

    - **meeting_id**: Meeting ID (required)

    Returns the meeting if it belongs to the current user.
    """
    meeting_service = MeetingService(db)
    meeting = await meeting_service.get_meeting_by_id(
        meeting_id=meeting_id,
        user_id=current_user["id"],
    )
    return meeting


@router.put("/{meeting_id}", response_model=MeetingResponse)
async def update_meeting(
    meeting_id: str,
    meeting_data: MeetingUpdate,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Update an existing meeting.

    Only scheduled or active meetings can be updated.

    - **meeting_id**: Meeting ID (required)
    - **scheduled_at**: New scheduled time (optional)
    - **duration_minutes**: New duration (optional)
    - **notes**: New notes (optional)

    Returns the updated meeting.
    """
    meeting_service = MeetingService(db)
    meeting = await meeting_service.update_meeting(
        meeting_id=meeting_id,
        user_id=current_user["id"],
        meeting_data=meeting_data,
    )
    return meeting


@router.put("/{meeting_id}/reschedule", response_model=MeetingResponse)
async def reschedule_meeting(
    meeting_id: str,
    reschedule_data: MeetingReschedule,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Reschedule a meeting to a new time.

    - **meeting_id**: Meeting ID (required)
    - **scheduled_at**: New scheduled time (required)
    - **notes**: Optional notes about rescheduling

    Returns the updated meeting.
    """
    meeting_service = MeetingService(db)
    meeting = await meeting_service.reschedule_meeting(
        meeting_id=meeting_id,
        user_id=current_user["id"],
        reschedule_data=reschedule_data,
    )
    return meeting


@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_meeting(
    meeting_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Cancel a meeting.

    Only scheduled or active meetings can be cancelled.

    - **meeting_id**: Meeting ID (required)

    Returns 204 No Content on success.
    """
    meeting_service = MeetingService(db)
    await meeting_service.cancel_meeting(
        meeting_id=meeting_id,
        user_id=current_user["id"],
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{meeting_id}/complete", response_model=MeetingResponse)
async def complete_meeting(
    meeting_id: str,
    complete_data: Optional[MeetingComplete] = None,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """
    Mark a meeting as completed.

    This will also create the next scheduled meeting based on the user's
    meeting interval setting.

    - **meeting_id**: Meeting ID (required)
    - **notes**: Optional notes from the meeting

    Returns the completed meeting.
    """
    meeting_service = MeetingService(db)

    notes = None
    if complete_data:
        notes = complete_data.notes

    meeting = await meeting_service.complete_meeting(
        meeting_id=meeting_id,
        user_id=current_user["id"],
        notes=notes,
    )
    return meeting
