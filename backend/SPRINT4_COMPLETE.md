# Sprint 4 Complete: Meeting Scheduling & Calendar

**Completed:** 2026-01-12

## Summary

Sprint 4 implements the meeting scheduling system for GoalGetter, including the ability to schedule, manage, and track coaching meetings. This sprint also implements user profile management and the critical phase transition logic that moves users from "goal_setting" to "tracking" phase.

## Files Created

### Models
- `backend/app/models/meeting.py` - Meeting document model with:
  - Meeting document creation and serialization
  - Meeting window calculations (30 min before to 60 min after)
  - Next meeting time calculation for recurring meetings
  - Status validation (scheduled, active, completed, cancelled)

### Schemas
- `backend/app/schemas/meeting.py` - Pydantic schemas including:
  - `MeetingCreate` - Create new meeting
  - `MeetingSetup` - Configure recurring meetings
  - `MeetingReschedule` - Reschedule a meeting
  - `MeetingUpdate` - Update meeting details
  - `MeetingComplete` - Complete a meeting
  - `MeetingResponse` - Meeting API response
  - `MeetingListResponse` - Paginated meeting list
  - `MeetingAccessResponse` - Chat access check result
  - `NextMeetingResponse` - Next meeting with countdown

### Services
- `backend/app/services/meeting_service.py` - Meeting business logic:
  - CRUD operations for meetings
  - Setup recurring meetings with configurable interval
  - Get active/next meeting
  - Check chat access based on phase and meeting window
  - Complete meeting and auto-create next one
  - Update meeting statuses (for background tasks)

- `backend/app/services/calendar_service.py` - Google Calendar integration:
  - Optional integration (only if GOOGLE_CLIENT_ID configured)
  - Event creation, update, and deletion stubs
  - OAuth URL generation
  - Calendar status endpoint
  - Graceful fallback when not configured

### Routes
- `backend/app/api/routes/meetings.py` - Meeting endpoints:
  - `POST /api/v1/meetings/setup` - Configure recurring meetings
  - `POST /api/v1/meetings` - Create new meeting
  - `GET /api/v1/meetings` - List meetings (paginated)
  - `GET /api/v1/meetings/next` - Get next meeting with countdown
  - `GET /api/v1/meetings/access` - Check chat access
  - `GET /api/v1/meetings/calendar/status` - Calendar integration status
  - `GET /api/v1/meetings/{id}` - Get specific meeting
  - `PUT /api/v1/meetings/{id}` - Update meeting
  - `PUT /api/v1/meetings/{id}/reschedule` - Reschedule meeting
  - `DELETE /api/v1/meetings/{id}` - Cancel meeting
  - `POST /api/v1/meetings/{id}/complete` - Mark meeting complete

- `backend/app/api/routes/users.py` - User profile endpoints:
  - `GET /api/v1/users/me` - Get current user profile
  - `PUT /api/v1/users/me` - Update profile
  - `PATCH /api/v1/users/me/phase` - Transition phase (with meeting setup)
  - `GET /api/v1/users/me/phase` - Get current phase
  - `DELETE /api/v1/users/me` - Delete account
  - `GET /api/v1/users/me/settings` - Get user settings
  - `PUT /api/v1/users/me/settings` - Update settings

### Modified Files
- `backend/app/main.py` - Added meetings and users routers

## API Endpoints Added

### Meetings Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/meetings/setup` | Configure recurring meeting schedule |
| POST | `/api/v1/meetings` | Create a new meeting |
| GET | `/api/v1/meetings` | List all meetings (with pagination/filters) |
| GET | `/api/v1/meetings/next` | Get next scheduled meeting |
| GET | `/api/v1/meetings/access` | Check if chat is accessible |
| GET | `/api/v1/meetings/calendar/status` | Get calendar integration status |
| GET | `/api/v1/meetings/{id}` | Get specific meeting |
| PUT | `/api/v1/meetings/{id}` | Update meeting details |
| PUT | `/api/v1/meetings/{id}/reschedule` | Reschedule to new time |
| DELETE | `/api/v1/meetings/{id}` | Cancel a meeting |
| POST | `/api/v1/meetings/{id}/complete` | Mark meeting as completed |

### Users Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/users/me` | Get current user profile |
| PUT | `/api/v1/users/me` | Update user profile |
| PATCH | `/api/v1/users/me/phase` | Transition to new phase |
| GET | `/api/v1/users/me/phase` | Get current phase info |
| DELETE | `/api/v1/users/me` | Delete user account |
| GET | `/api/v1/users/me/settings` | Get user settings |
| PUT | `/api/v1/users/me/settings` | Update user settings |

## Key Features Implemented

### 1. Meeting Scheduling
- Create individual meetings or set up recurring schedule
- Configurable meeting interval (1-90 days)
- Configurable meeting duration (15-180 minutes)
- Preferred meeting time (hour/minute)

### 2. Meeting Window Access Control
- **Window Start:** 30 minutes before scheduled time
- **Window End:** 60 minutes after meeting end time
- Chat is only accessible during meeting windows in tracking phase
- Goal setting phase has unlimited chat access

### 3. Phase Transition Logic
When a user transitions from "goal_setting" to "tracking":
1. User's phase is updated to "tracking"
2. Meeting interval and duration are configured
3. First meeting is automatically created
4. Subsequent meetings are auto-created when marking meetings complete

### 4. Google Calendar Integration (Optional)
- Only active when `GOOGLE_CLIENT_ID` is configured
- Graceful fallback when not configured
- Prepared structure for OAuth flow
- Event creation/update/deletion stubs ready for implementation

### 5. User Profile Management
- View and update profile
- Manage settings (timezone, notifications, meeting duration)
- Delete account (cascades to goals, meetings, chat messages)

## Meeting Access Logic

```python
def can_access_chat(user):
    if user.phase == "goal_setting":
        return True  # Unlimited access

    # In tracking phase
    active_meeting = get_active_meeting_in_window(user)
    if active_meeting:
        return True  # Within meeting window

    return False  # Outside meeting window
```

## Testing the Implementation

### Start the Server
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

### Test Meeting Endpoints (with valid JWT token)

1. **Check Chat Access:**
```bash
curl -X GET "http://localhost:8000/api/v1/meetings/access" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

2. **Setup Recurring Meetings:**
```bash
curl -X POST "http://localhost:8000/api/v1/meetings/setup" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "interval_days": 7,
    "duration_minutes": 30,
    "preferred_hour": 9,
    "preferred_minute": 0
  }'
```

3. **Transition to Tracking Phase:**
```bash
curl -X PATCH "http://localhost:8000/api/v1/users/me/phase" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "phase": "tracking",
    "meeting_setup": {
      "interval_days": 7,
      "duration_minutes": 30
    }
  }'
```

4. **Get Next Meeting:**
```bash
curl -X GET "http://localhost:8000/api/v1/meetings/next" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

5. **List All Meetings:**
```bash
curl -X GET "http://localhost:8000/api/v1/meetings?upcoming_only=true" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Configuration Used

Meeting settings from `app/core/config.py`:
- `MEETING_WINDOW_BEFORE_MINUTES`: 30
- `MEETING_WINDOW_AFTER_MINUTES`: 60
- `DEFAULT_MEETING_DURATION_MINUTES`: 30
- `DEFAULT_MEETING_INTERVAL_DAYS`: 7

## Notes for Next Sprint

1. **Celery Integration:** The `update_meeting_statuses()` method in MeetingService is ready to be called by a Celery periodic task to automatically update meeting statuses.

2. **Email Notifications:** Meeting creation and reminders should trigger email notifications (to be implemented in Sprint 5).

3. **Calendar Sync:** Google Calendar service is structured but needs the `google-api-python-client` library for full implementation. Consider adding as optional dependency.

4. **Background Tasks Needed:**
   - Update meeting statuses (every 5 minutes)
   - Send meeting reminders (24h and 1h before)
   - Auto-create next meeting when one expires

## Dependencies

No new dependencies were required for this sprint. All functionality uses existing packages.

## Sprint Status

- [x] Create Meeting model
- [x] Create Meeting schemas
- [x] Create Meeting service with CRUD operations
- [x] Create Calendar service (optional Google Calendar)
- [x] Create Meetings router
- [x] Create Users router
- [x] Implement phase transition logic
- [x] Register routers in main.py
- [x] Test implementation
- [x] Update sprint tracker

**Sprint 4 is complete. Ready for Sprint 5: Notifications & Background Jobs.**
