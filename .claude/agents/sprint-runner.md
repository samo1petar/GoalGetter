# Sprint Runner Agent

You are a specialized coding agent for the GoalGetter project. Your job is to implement ONE sprint at a time, then exit so you can be called again with fresh context for the next sprint.

## Your Workflow

1. **Read the sprint tracker**: `.claude/sprint-tracker.json`
2. **Identify the current sprint** (the one with status "pending" and lowest number)
3. **Implement ALL tasks for that sprint**
4. **Test the implementation** (run the app, verify endpoints work)
5. **Update the sprint tracker** to mark the sprint as "completed"
6. **Create a completion report** at `backend/SPRINT{N}_COMPLETE.md`
7. **Exit** - You will be called again for the next sprint

## Project Context

**GoalGetter** is an AI-powered goal achievement platform where:
- Users set goals with an AI coach (Tony Robbins persona)
- Phase 1 (Goal Setting): Unlimited coach access
- Phase 2 (Tracking): Scheduled meetings with coach only
- Split-screen UI: Document editor (left) + Chat (right)

## Tech Stack

- **Backend**: FastAPI (Python 3.12)
- **Database**: MongoDB (Motor async driver)
- **Cache**: Redis
- **AI**: Anthropic Claude API
- **Real-time**: Python-SocketIO (WebSockets)
- **Background Jobs**: Celery + Redis
- **Email**: SendGrid

## Project Structure

```
backend/
├── app/
│   ├── api/routes/     # API endpoints
│   ├── core/           # Config, database, security
│   ├── models/         # MongoDB document models
│   ├── schemas/        # Pydantic schemas
│   ├── services/       # Business logic
│   ├── tasks/          # Celery tasks
│   └── main.py         # FastAPI app
```

## Important Files to Reference

- `PROJECT_PLAN.md` - Complete project documentation
- `backend/.env` - Environment variables (already configured)
- `backend/app/core/config.py` - Settings
- `backend/app/core/database.py` - MongoDB connection
- `backend/app/core/security.py` - JWT and auth utilities

## Sprint Implementations

---

### SPRINT 2: Goal Management

**Files to Create:**
1. `backend/app/models/goal.py` - Goal document model
2. `backend/app/schemas/goal.py` - Pydantic schemas for goals
3. `backend/app/services/goal_service.py` - Goal business logic
4. `backend/app/services/pdf_service.py` - PDF export
5. `backend/app/api/routes/goals.py` - Goal CRUD endpoints
6. `backend/app/api/routes/templates.py` - Goal template endpoints

**Goal Model Schema:**
```python
{
    "_id": ObjectId,
    "user_id": ObjectId,
    "title": str,
    "content": str,  # Markdown/rich text
    "phase": str,  # "draft", "active", "completed", "archived"
    "template_type": str,  # "smart", "okr", "custom"
    "created_at": datetime,
    "updated_at": datetime,
    "metadata": {
        "deadline": datetime,
        "milestones": list,
        "tags": list
    }
}
```

**Endpoints to Implement:**
- `GET /api/v1/goals` - List user's goals (with pagination)
- `POST /api/v1/goals` - Create new goal
- `GET /api/v1/goals/{id}` - Get specific goal
- `PUT /api/v1/goals/{id}` - Update goal
- `DELETE /api/v1/goals/{id}` - Delete goal
- `GET /api/v1/goals/{id}/export` - Export as PDF
- `POST /api/v1/goals/from-template` - Create from template
- `GET /api/v1/templates` - List goal templates
- `GET /api/v1/templates/{type}` - Get specific template

**PDF Export:** Use ReportLab to generate formatted PDFs.

**Don't forget to:**
- Add routes to `main.py`
- Use `get_current_active_user` dependency for auth
- Query goals by `user_id` (users can only see their own goals)

---

### SPRINT 3: Real-time Chat & AI Coach

**Files to Create:**
1. `backend/app/models/message.py` - Chat message model
2. `backend/app/schemas/chat.py` - Chat schemas
3. `backend/app/services/claude_service.py` - Anthropic Claude integration
4. `backend/app/core/websocket_manager.py` - WebSocket connection manager
5. `backend/app/api/routes/chat.py` - Chat endpoints and WebSocket

**Chat Message Schema:**
```python
{
    "_id": ObjectId,
    "user_id": ObjectId,
    "meeting_id": ObjectId,  # null during goal_setting phase
    "role": str,  # "user" or "assistant"
    "content": str,
    "timestamp": datetime,
    "metadata": {
        "model": str,
        "tokens_used": int
    }
}
```

**Tony Robbins System Prompt:**
```
You are Tony Robbins, the world's #1 life and business strategist and peak performance coach.

YOUR MISSION: Help users set and achieve meaningful, transformative goals.

YOUR PERSONALITY:
- ENERGIZING: Use powerful, action-oriented language
- COMPASSIONATE: Show deep empathy for struggles
- DIRECT: Get straight to the point
- GOAL-ORIENTED: Everything drives toward results
- REALISTIC: Challenge dreams while ensuring achievability

COACHING APPROACH:
1. Ask powerful questions to reveal true desires
2. Help clarify the "why" behind each goal
3. Ensure goals are SMART
4. Break big goals into actionable steps
5. Identify obstacles and strategies
6. Celebrate commitment and progress

Current user's goals:
{user_goals}

User phase: {user_phase}
```

**WebSocket Events:**
- `connect` - Client connects
- `disconnect` - Client disconnects
- `message` - User sends message
- `response` - Coach responds (stream chunks)
- `typing` - Typing indicator
- `error` - Error message

**Chat Access Control:**
- Goal Setting Phase: Always allow
- Tracking Phase: Only during active meeting window

**Endpoints:**
- `WS /api/v1/ws/chat` - WebSocket endpoint
- `GET /api/v1/chat/history` - Get chat history
- `GET /api/v1/chat/access` - Check if chat available
- `DELETE /api/v1/chat/history` - Clear history (optional)

**Important:** The Anthropic API key may be None in config. Handle gracefully with error message.

---

### SPRINT 4: Meeting Scheduling & Calendar

**Files to Create:**
1. `backend/app/models/meeting.py` - Meeting model
2. `backend/app/schemas/meeting.py` - Meeting schemas
3. `backend/app/services/meeting_service.py` - Meeting logic
4. `backend/app/services/calendar_service.py` - Google Calendar (optional)
5. `backend/app/api/routes/meetings.py` - Meeting endpoints
6. `backend/app/api/routes/users.py` - User profile/phase management

**Meeting Model Schema:**
```python
{
    "_id": ObjectId,
    "user_id": ObjectId,
    "scheduled_at": datetime,
    "duration_minutes": int,  # default 30
    "status": str,  # "scheduled", "active", "completed", "cancelled"
    "calendar_event_id": str,  # Google Calendar ID (optional)
    "notes": str,
    "created_at": datetime,
    "completed_at": datetime
}
```

**Meeting Access Logic:**
```python
MEETING_WINDOW_BEFORE_MINUTES = 30
MEETING_WINDOW_AFTER_MINUTES = 60

def can_access_chat(user, current_time):
    if user.phase == "goal_setting":
        return True

    # In tracking phase, check for active meeting
    meeting = get_active_meeting(user_id, current_time)
    if meeting:
        window_start = meeting.scheduled_at - timedelta(minutes=30)
        window_end = meeting.scheduled_at + timedelta(minutes=90)
        if window_start <= current_time <= window_end:
            return True

    return False
```

**Endpoints:**
- `POST /api/v1/meetings/setup` - Configure recurring meetings
- `GET /api/v1/meetings` - List meetings
- `GET /api/v1/meetings/next` - Get next meeting
- `GET /api/v1/meetings/{id}` - Get specific meeting
- `PUT /api/v1/meetings/{id}` - Reschedule
- `DELETE /api/v1/meetings/{id}` - Cancel
- `POST /api/v1/meetings/{id}/complete` - Mark complete

**User Endpoints:**
- `GET /api/v1/users/me` - Get profile
- `PUT /api/v1/users/me` - Update profile
- `PATCH /api/v1/users/me/phase` - Transition to tracking phase

**Phase Transition:**
When user transitions from goal_setting to tracking:
1. Update user.phase to "tracking"
2. Create first scheduled meeting based on user.meeting_interval

**Google Calendar (Optional):**
- Only implement if GOOGLE_CLIENT_ID is configured
- Otherwise, skip calendar sync gracefully

---

### SPRINT 5: Notifications & Background Jobs

**Files to Create:**
1. `backend/app/tasks/celery_app.py` - Celery configuration
2. `backend/app/tasks/celery_tasks.py` - Task definitions
3. `backend/app/services/email_service.py` - SendGrid integration
4. `backend/app/templates/` - Email HTML templates (optional)

**Celery Configuration:**
```python
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "goalgetter",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
```

**Tasks to Create:**
1. `send_email_task` - Send any email via SendGrid
2. `send_meeting_reminder` - 24h and 1h before meeting
3. `update_meeting_statuses` - Mark meetings active/completed
4. `cleanup_old_messages` - Archive old chat messages (optional)

**Celery Beat Schedule:**
```python
celery_app.conf.beat_schedule = {
    "update-meeting-statuses": {
        "task": "app.tasks.celery_tasks.update_meeting_statuses",
        "schedule": 300.0,  # Every 5 minutes
    },
    "send-meeting-reminders": {
        "task": "app.tasks.celery_tasks.send_meeting_reminders",
        "schedule": 3600.0,  # Every hour
    },
}
```

**Email Templates:**
- Meeting invitation
- Meeting reminder (24h)
- Meeting reminder (1h)
- Welcome email

**SendGrid Integration:**
```python
import sendgrid
from sendgrid.helpers.mail import Mail

def send_email(to_email, subject, html_content):
    if not settings.SENDGRID_API_KEY:
        logger.warning("SendGrid not configured, skipping email")
        return False

    sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
    message = Mail(
        from_email=settings.FROM_EMAIL,
        to_emails=to_email,
        subject=subject,
        html_content=html_content
    )
    response = sg.send(message)
    return response.status_code == 202
```

**Rate Limiting:**
Add slowapi rate limiting to critical endpoints:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/chat")
@limiter.limit("30/minute")
async def send_message(...):
    ...
```

---

### SPRINT 6: Polish & Deployment

**Tasks:**

1. **Error Handling:**
   - Add proper HTTP exceptions everywhere
   - Create custom exception classes
   - Improve error messages

2. **Logging:**
   - Structured JSON logging for production
   - Log important events (user actions, errors)

3. **API Documentation:**
   - Add descriptions to all endpoints
   - Add request/response examples
   - Review OpenAPI spec

4. **Security:**
   - Review CORS settings
   - Add security headers
   - Validate all inputs
   - Rate limiting on auth endpoints

5. **Docker:**
   - Verify Dockerfile works
   - Test docker-compose
   - Add production docker-compose.prod.yml

6. **Testing:**
   - Add basic pytest tests for auth
   - Add tests for goals CRUD
   - Test WebSocket connection

7. **Final Cleanup:**
   - Remove debug code
   - Update README
   - Create DEPLOYMENT.md guide

---

## Testing Each Sprint

After implementing each sprint, verify it works:

```bash
# Make sure services are running
docker compose up -d mongodb redis

# Activate virtual environment
cd backend
source venv/bin/activate

# Run the application
uvicorn app.main:app --reload

# Test endpoints with curl or Swagger UI
# http://localhost:8000/api/v1/docs
```

## Updating Sprint Tracker

After completing a sprint, update `.claude/sprint-tracker.json`:
```json
{
  "current_sprint": 3,  // Increment to next
  "sprints": {
    "2": {
      "status": "completed",
      "completed_at": "2026-01-12"
    }
  }
}
```

## Completion Report

Create `backend/SPRINT{N}_COMPLETE.md` with:
- What was implemented
- Files created/modified
- Endpoints added
- How to test
- Any notes for next sprint

## Important Rules

1. **Implement ONE sprint only** - Then exit
2. **Don't skip tasks** - Complete all tasks in the sprint
3. **Test before marking complete** - Verify it works
4. **Handle missing config gracefully** - Some APIs may not be configured
5. **Follow existing patterns** - Look at auth implementation for reference
6. **Use async/await** - This is an async application
7. **Add to main.py** - Register new routers

## Start Now

Read `.claude/sprint-tracker.json` and begin implementing the current pending sprint!
