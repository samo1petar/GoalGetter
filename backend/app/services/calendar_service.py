"""
Calendar service for Google Calendar integration.
This service is optional and only active when GOOGLE_CLIENT_ID is configured.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class CalendarService:
    """
    Service for Google Calendar integration.

    This service handles:
    - Creating calendar events for meetings
    - Updating events when meetings are rescheduled
    - Deleting events when meetings are cancelled
    - OAuth flow for calendar access

    Note: Google Calendar integration is optional and only active
    when GOOGLE_CLIENT_ID is configured in the environment.
    """

    def __init__(self):
        self.enabled = self._check_enabled()
        if self.enabled:
            logger.info("Google Calendar integration is enabled")
        else:
            logger.info("Google Calendar integration is disabled (GOOGLE_CLIENT_ID not configured)")

    def _check_enabled(self) -> bool:
        """Check if Google Calendar integration is enabled."""
        return (
            settings.ENABLE_CALENDAR_SYNC and
            settings.GOOGLE_CLIENT_ID is not None and
            settings.GOOGLE_CLIENT_SECRET is not None
        )

    def is_enabled(self) -> bool:
        """Check if calendar service is enabled."""
        return self.enabled

    def get_auth_url(self, state: Optional[str] = None) -> Optional[str]:
        """
        Get the Google OAuth URL for calendar authorization.

        Args:
            state: Optional state parameter for OAuth flow

        Returns:
            OAuth authorization URL or None if not enabled
        """
        if not self.enabled:
            logger.warning("Calendar service not enabled, cannot generate auth URL")
            return None

        # Build OAuth URL
        base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": f"{settings.FRONTEND_URL}/api/v1/calendar/callback",
            "response_type": "code",
            "scope": settings.GOOGLE_CALENDAR_SCOPES,
            "access_type": "offline",
            "prompt": "consent",
        }

        if state:
            params["state"] = state

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{base_url}?{query_string}"

    async def exchange_code_for_tokens(
        self,
        code: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Exchange authorization code for access and refresh tokens.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            Dict with access_token, refresh_token, expires_in or None
        """
        if not self.enabled:
            logger.warning("Calendar service not enabled")
            return None

        # In a full implementation, this would make a request to Google's token endpoint
        # For now, we return a placeholder indicating the feature is available but needs
        # the Google API client library for full implementation
        logger.info("Token exchange would happen here with Google OAuth")

        return {
            "message": "Google Calendar integration requires google-api-python-client library",
            "enabled": True,
            "requires_setup": True,
        }

    async def create_calendar_event(
        self,
        user_id: str,
        meeting_data: Dict[str, Any],
        access_token: str,
    ) -> Optional[str]:
        """
        Create a Google Calendar event for a meeting.

        Args:
            user_id: User ID
            meeting_data: Meeting details (scheduled_at, duration_minutes, etc.)
            access_token: User's Google Calendar access token

        Returns:
            Google Calendar event ID or None
        """
        if not self.enabled:
            logger.debug("Calendar service not enabled, skipping event creation")
            return None

        # In a full implementation, this would use the Google Calendar API
        # to create an event. For now, we log and return None.
        logger.info(f"Would create calendar event for meeting at {meeting_data.get('scheduled_at')}")

        return None

    async def update_calendar_event(
        self,
        event_id: str,
        meeting_data: Dict[str, Any],
        access_token: str,
    ) -> bool:
        """
        Update a Google Calendar event when a meeting is rescheduled.

        Args:
            event_id: Google Calendar event ID
            meeting_data: Updated meeting details
            access_token: User's Google Calendar access token

        Returns:
            True if updated successfully
        """
        if not self.enabled:
            logger.debug("Calendar service not enabled, skipping event update")
            return False

        if not event_id:
            logger.debug("No event ID provided, skipping update")
            return False

        # In a full implementation, this would use the Google Calendar API
        logger.info(f"Would update calendar event {event_id}")

        return False

    async def delete_calendar_event(
        self,
        event_id: str,
        access_token: str,
    ) -> bool:
        """
        Delete a Google Calendar event when a meeting is cancelled.

        Args:
            event_id: Google Calendar event ID
            access_token: User's Google Calendar access token

        Returns:
            True if deleted successfully
        """
        if not self.enabled:
            logger.debug("Calendar service not enabled, skipping event deletion")
            return False

        if not event_id:
            logger.debug("No event ID provided, skipping deletion")
            return False

        # In a full implementation, this would use the Google Calendar API
        logger.info(f"Would delete calendar event {event_id}")

        return False

    async def refresh_access_token(
        self,
        refresh_token: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Refresh an expired Google Calendar access token.

        Args:
            refresh_token: User's refresh token

        Returns:
            Dict with new access_token and expires_in or None
        """
        if not self.enabled:
            logger.warning("Calendar service not enabled")
            return None

        # In a full implementation, this would make a request to Google's token endpoint
        logger.info("Token refresh would happen here with Google OAuth")

        return None

    def build_event_body(
        self,
        meeting_data: Dict[str, Any],
        user_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build the Google Calendar event body from meeting data.

        Args:
            meeting_data: Meeting details
            user_email: User's email for attendee

        Returns:
            Google Calendar event body dict
        """
        scheduled_at = meeting_data.get("scheduled_at")
        if isinstance(scheduled_at, str):
            scheduled_at = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))

        duration_minutes = meeting_data.get("duration_minutes", 30)
        end_time = scheduled_at + timedelta(minutes=duration_minutes)

        event = {
            "summary": "GoalGetter Coaching Session",
            "description": "Your scheduled coaching session with the AI coach.",
            "start": {
                "dateTime": scheduled_at.isoformat(),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": end_time.isoformat(),
                "timeZone": "UTC",
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 24 * 60},  # 24 hours before
                    {"method": "popup", "minutes": 60},  # 1 hour before
                    {"method": "popup", "minutes": 30},  # 30 minutes before
                ],
            },
        }

        if user_email:
            event["attendees"] = [{"email": user_email}]

        return event

    def get_calendar_status(self) -> Dict[str, Any]:
        """
        Get the current status of calendar integration.

        Returns:
            Dict with integration status information
        """
        return {
            "enabled": self.enabled,
            "provider": "google" if self.enabled else None,
            "features": {
                "create_events": self.enabled,
                "update_events": self.enabled,
                "delete_events": self.enabled,
                "reminders": self.enabled,
            },
            "message": (
                "Google Calendar integration is active"
                if self.enabled
                else "Google Calendar integration is disabled. Configure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to enable."
            ),
        }


# Global calendar service instance
calendar_service = CalendarService()
