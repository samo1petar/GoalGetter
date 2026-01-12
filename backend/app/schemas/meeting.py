"""
Pydantic schemas for Meeting-related requests and responses.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class MeetingBase(BaseModel):
    """Base meeting schema with common fields."""
    scheduled_at: datetime
    duration_minutes: int = Field(default=30, ge=15, le=180)


class MeetingCreate(MeetingBase):
    """Schema for creating a new meeting."""
    notes: Optional[str] = Field(None, max_length=5000)


class MeetingSetup(BaseModel):
    """Schema for setting up recurring meetings."""
    interval_days: int = Field(..., ge=1, le=90, description="Days between meetings")
    first_meeting_at: Optional[datetime] = Field(
        None,
        description="Optional specific time for first meeting"
    )
    duration_minutes: int = Field(default=30, ge=15, le=180)
    preferred_hour: int = Field(default=9, ge=0, le=23, description="Preferred meeting hour (UTC)")
    preferred_minute: int = Field(default=0, ge=0, le=59, description="Preferred meeting minute")


class MeetingReschedule(BaseModel):
    """Schema for rescheduling a meeting."""
    scheduled_at: datetime
    notes: Optional[str] = Field(None, max_length=5000)


class MeetingUpdate(BaseModel):
    """Schema for updating meeting details."""
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, ge=15, le=180)
    notes: Optional[str] = Field(None, max_length=5000)


class MeetingComplete(BaseModel):
    """Schema for completing a meeting."""
    notes: Optional[str] = Field(None, max_length=5000)


class MeetingResponse(BaseModel):
    """Schema for meeting response."""
    id: str
    user_id: str
    scheduled_at: str
    duration_minutes: int
    status: str
    calendar_event_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None

    class Config:
        from_attributes = True


class MeetingListResponse(BaseModel):
    """Schema for paginated meeting list response."""
    meetings: List[MeetingResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class MeetingAccessResponse(BaseModel):
    """Schema for meeting access check response."""
    can_access: bool
    reason: str
    current_phase: str
    active_meeting: Optional[MeetingResponse] = None
    next_meeting: Optional[MeetingResponse] = None
    window_start: Optional[str] = None
    window_end: Optional[str] = None


class NextMeetingResponse(BaseModel):
    """Schema for next meeting response."""
    meeting: Optional[MeetingResponse] = None
    message: str
    can_access_now: bool
    countdown_seconds: Optional[int] = None
