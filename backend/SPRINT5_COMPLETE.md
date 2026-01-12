# Sprint 5 Complete: Notifications & Background Jobs

**Completed:** 2026-01-12
**Sprint Duration:** Estimated 3-4 days

## Summary

Sprint 5 implements the background processing infrastructure for GoalGetter, including:
- Celery task queue with Redis broker
- SendGrid email service integration
- Meeting reminder system (24h and 1h before)
- Automated meeting status updates
- Rate limiting on critical API endpoints

## Files Created

### 1. Celery Configuration (`backend/app/tasks/celery_app.py`)
- Celery application setup with Redis broker
- Beat schedule for periodic tasks:
  - `update-meeting-statuses`: Every 5 minutes
  - `send-meeting-reminders`: Every hour
  - `cleanup-old-messages`: Daily at 3 AM UTC
- Task queue configuration (default, email, high_priority)

### 2. Celery Tasks (`backend/app/tasks/celery_tasks.py`)
Tasks implemented:
- **`send_email_task`**: Generic email sending with retry logic
- **`send_meeting_reminders_task`**: Sends 24h and 1h meeting reminders
- **`update_meeting_statuses_task`**: Updates meeting statuses (scheduled -> active -> completed)
- **`cleanup_old_messages_task`**: Removes chat messages older than 90 days
- **`send_welcome_email_task`**: Convenience task for welcome emails
- **`send_phase_transition_email_task`**: Notifies users of phase changes
- **`health_check`**: Verifies Celery worker is operational

### 3. Email Service (`backend/app/services/email_service.py`)
Email types supported:
- **Welcome email**: Sent to new users on signup
- **Meeting invitation**: Sent when meetings are scheduled
- **Meeting reminder**: 24h and 1h before meetings
- **Goal milestone**: Celebrates goal achievements
- **Phase transition**: Notifies when moving to tracking phase

Features:
- Graceful degradation when SendGrid is not configured
- HTML and plain text versions
- Consistent branding with Tony Robbins persona
- Support email and frontend URL integration

### 4. Email Templates (`backend/app/templates/`)
- `email/__init__.py`: Package initialization
- `email/base.html`: Base HTML template with styling

### 5. Updated Files

#### `backend/app/main.py`
- Added slowapi rate limiter initialization
- Configured rate limit exception handler
- Uses Redis for distributed rate limiting in production

#### `backend/app/api/routes/auth.py`
Rate limits applied:
- `/signup`: 5 requests/minute (strict)
- `/login`: 10 requests/minute (strict)
- `/refresh`: 30 requests/minute
- `/google`: 10 requests/minute

#### `backend/app/api/routes/chat.py`
Rate limits applied:
- `/access`: 30 requests/minute
- `/history`: 30 requests/minute
- `/send`: 30 requests/minute (AI API cost control)

## Configuration

### Environment Variables (already in config.py)
```
# SendGrid
SENDGRID_API_KEY=SG.your-api-key
FROM_EMAIL=noreply@goalgetter.com
FROM_NAME=GoalGetter
SUPPORT_EMAIL=support@goalgetter.com

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
```

### SendGrid Setup
1. Create a SendGrid account
2. Generate an API key
3. Add `SENDGRID_API_KEY` to `.env`

**Note:** Email sending is optional - the service logs warnings if SendGrid is not configured but continues to operate.

## Running Celery Workers

### Start Celery Worker
```bash
cd backend
celery -A app.tasks.celery_app worker --loglevel=info
```

### Start Celery Beat (Scheduler)
```bash
cd backend
celery -A app.tasks.celery_app beat --loglevel=info
```

### Combined Worker + Beat (Development)
```bash
cd backend
celery -A app.tasks.celery_app worker --beat --loglevel=info
```

### Flower (Monitoring Dashboard)
```bash
cd backend
celery -A app.tasks.celery_app flower
# Access at http://localhost:5555
```

## Testing

### Test Email Service
```python
from app.services.email_service import email_service

# Test welcome email (will log warning if SendGrid not configured)
result = email_service.send_welcome_email(
    "test@example.com",
    "Test User"
)
print(f"Email sent: {result}")
```

### Test Celery Tasks
```python
from app.tasks.celery_tasks import health_check, send_email_task

# Health check
result = health_check.delay()
print(result.get(timeout=10))

# Send email task
result = send_email_task.delay(
    email_type="welcome",
    to_email="test@example.com",
    user_name="Test User"
)
print(result.get(timeout=30))
```

### Test Rate Limiting
```bash
# Should succeed
curl http://localhost:8000/api/v1/auth/login -X POST ...

# After 10 requests in a minute, should return 429 Too Many Requests
for i in {1..15}; do
    curl -w "%{http_code}\n" http://localhost:8000/api/v1/auth/login -X POST -d '...'
done
```

## Meeting Reminder Flow

1. **24-hour reminder**: Task checks for meetings 23-25 hours away
2. **1-hour reminder**: Task checks for meetings 50-70 minutes away
3. Reminders are only sent to users with `email_notifications` enabled
4. Each reminder is tracked (`reminder_24h_sent`, `reminder_1h_sent`) to prevent duplicates

## Meeting Status Updates

The `update_meeting_statuses_task` runs every 5 minutes and:
1. Marks `scheduled` meetings as `active` when within the meeting window
2. Marks `active` meetings as `completed` when window expires
3. Creates next meeting for users in tracking phase
4. Sends meeting invitation emails for newly created meetings

## Dependencies

All required packages are already in `requirements.txt`:
- `celery==5.3.6`
- `flower==2.0.1`
- `sendgrid==6.11.0`
- `slowapi==0.1.9`

## Docker Compose Addition

Add Celery services to `docker-compose.yml`:
```yaml
services:
  celery-worker:
    build: ./backend
    command: celery -A app.tasks.celery_app worker --loglevel=info
    depends_on:
      - redis
      - mongodb
    env_file:
      - ./backend/.env

  celery-beat:
    build: ./backend
    command: celery -A app.tasks.celery_app beat --loglevel=info
    depends_on:
      - redis
      - mongodb
    env_file:
      - ./backend/.env
```

## Notes for Next Sprint (Sprint 6)

1. **Logging**: Add structured JSON logging for Celery tasks
2. **Error Handling**: Add Sentry integration for Celery error tracking
3. **Testing**: Add unit tests for email service and Celery tasks
4. **Docker**: Finalize Celery worker and beat containers
5. **Security**: Review rate limits based on expected usage patterns

## API Rate Limits Summary

| Endpoint | Limit | Reason |
|----------|-------|--------|
| POST /auth/signup | 5/min | Prevent abuse |
| POST /auth/login | 10/min | Brute force protection |
| POST /auth/refresh | 30/min | Normal usage |
| GET /auth/google | 10/min | OAuth flow |
| GET /chat/access | 30/min | Frequent checks |
| GET /chat/history | 30/min | Normal usage |
| POST /chat/send | 30/min | API cost control |
| Global default | 60/min | General protection |
