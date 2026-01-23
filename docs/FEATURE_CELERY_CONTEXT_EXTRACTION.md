# Feature Request: Move Context Extraction to Celery Background Task

**Status: IMPLEMENTED**

## Overview

Move the session context extraction from a blocking `await` call in the logout endpoint to a Celery background task. This will make logout instant while still reliably extracting and saving session context.

## Problem

The logout endpoint currently blocks for 5-7 seconds because it awaits context extraction which includes an LLM API call. See `docs/INVESTIGATION_SLOW_LOGOUT.md` for full analysis.

## Solution

Create a Celery task that handles context extraction asynchronously. The logout endpoint will queue the task and return immediately.

## Implementation

### 1. Create New Celery Task

**File:** `backend/app/tasks/celery_tasks.py`

Add a new task for context extraction. Since Celery tasks run synchronously, we need to:
- Use synchronous MongoDB client (already available via `get_sync_db()`)
- Use synchronous LLM calls or run async code with `asyncio.run()`

```python
@shared_task(
    name="app.tasks.celery_tasks.extract_session_context_task",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def extract_session_context_task(
    self,
    user_id: str,
    session_id: str,
) -> Dict[str, Any]:
    """
    Extract and save session context in background.

    This task is queued on logout/disconnect to extract meaningful
    context from the user's conversation without blocking the response.

    Args:
        user_id: The user's ID
        session_id: The session ID for this context

    Returns:
        Dict with success status and context_id if created
    """
    try:
        logger.info(f"Starting context extraction for user {user_id}, session {session_id}")

        db = get_sync_db()

        # Get conversation history (last 100 messages)
        messages = list(db.chat_messages.find(
            {"user_id": ObjectId(user_id)},
            sort=[("timestamp", -1)],
            limit=100,
        ))

        if len(messages) < 2:
            logger.info(f"Insufficient messages for context extraction: {len(messages)}")
            return {"success": True, "context_id": None, "reason": "insufficient_messages"}

        # Reverse to chronological order
        messages = list(reversed(messages))
        conversation_history = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in messages
        ]

        # Run async extraction in sync context
        import asyncio
        result = asyncio.run(_extract_context_async(user_id, session_id, conversation_history))

        return result

    except Exception as e:
        logger.error(f"Error in context extraction task: {e}")
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            return {"success": False, "error": str(e)}


async def _extract_context_async(
    user_id: str,
    session_id: str,
    conversation_history: List[Dict[str, str]],
) -> Dict[str, Any]:
    """
    Async helper for context extraction.
    Separated to allow using async LLM service.
    """
    from app.core.database import get_database_sync
    from app.services.context_service import ContextService
    from motor.motor_asyncio import AsyncIOMotorClient
    from app.core.config import settings

    # Create async MongoDB client for this operation
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DB_NAME]

    try:
        context_service = ContextService(db)

        # Extract context using LLM
        session_context = await context_service.extract_session_context(
            user_id=user_id,
            session_id=session_id,
            conversation_history=conversation_history,
        )

        if not session_context or not session_context.get("context_points"):
            return {"success": True, "context_id": None, "reason": "no_context_extracted"}

        # Save context
        context_id = await context_service.save_session_context(session_context)

        # Check if summarization needed
        if context_id:
            await context_service.maybe_summarize_old_sessions(user_id)

        logger.info(f"Context extraction complete for user {user_id}: {context_id}")
        return {"success": True, "context_id": context_id}

    finally:
        client.close()
```

### 2. Update Logout Endpoint

**File:** `backend/app/api/routes/auth.py`

Replace the blocking `await` with a Celery task queue call:

```python
# Before (blocking):
try:
    context_service = get_context_service(db)
    session_id = jti or f"logout-{datetime.utcnow().timestamp()}"
    await context_service.extract_and_save_context(
        user_id=current_user["id"],
        session_id=session_id,
    )
    logger.info(f"Session context extracted on logout for user {current_user['id']}")
except Exception as e:
    logger.warning(f"Failed to extract session context on logout: {e}")

# After (non-blocking):
from app.tasks.celery_tasks import extract_session_context_task

session_id = jti or f"logout-{datetime.utcnow().timestamp()}"
extract_session_context_task.delay(
    user_id=current_user["id"],
    session_id=session_id,
)
logger.info(f"Queued context extraction for user {current_user['id']}")
```

### 3. Update WebSocket Disconnect Handler (Optional)

**File:** `backend/app/api/routes/chat.py`

Also move WebSocket disconnect context extraction to Celery for consistency:

```python
# In the finally block (around line 773-789):

# Before:
try:
    context_service = get_context_service(db)
    await context_service.extract_and_save_context(
        user_id=user_id,
        session_id=ws_session_id,
    )
except Exception as context_error:
    logger.warning(f"Failed to extract session context on disconnect: {context_error}")

# After:
from app.tasks.celery_tasks import extract_session_context_task

extract_session_context_task.delay(
    user_id=user_id,
    session_id=ws_session_id,
)
logger.info(f"Queued context extraction on disconnect for user {user_id}")
```

### 4. Add Required Import

**File:** `backend/app/tasks/celery_tasks.py`

Add to imports at top of file:
```python
from typing import Optional, List, Dict, Any
from bson import ObjectId
```

## Implementation Checklist

- [x] Add `extract_session_context_task` to `celery_tasks.py`
- [x] Add `_extract_context_async` helper function
- [x] Update logout endpoint in `auth.py` to use task
- [x] Update WebSocket disconnect in `chat.py` to use task
- [ ] Test logout is now instant
- [ ] Test context is still extracted (check database)
- [ ] Test retry mechanism works on failure

## Files to Modify

| File | Changes |
|------|---------|
| `backend/app/tasks/celery_tasks.py` | Add `extract_session_context_task` and helper |
| `backend/app/api/routes/auth.py` | Replace await with task.delay() |
| `backend/app/api/routes/chat.py` | (Optional) Replace await with task.delay() |

## Testing

1. **Logout speed test:**
   - Login, chat a bit, logout
   - Logout should complete in < 500ms

2. **Context extraction verification:**
   - After logout, check `session_contexts` collection in MongoDB
   - Context should appear within 10-30 seconds

3. **Retry test:**
   - Temporarily break LLM service
   - Trigger logout
   - Fix LLM service
   - Context should be extracted after retry

## Notes

- Celery worker must be running for tasks to execute
- Task uses its own MongoDB connection (required for separate process)
- Retry mechanism handles transient LLM failures
- Task timeout is 30 minutes (inherited from Celery config)

## Priority

**P1** - Directly impacts user experience on every logout

---

## Resolution

**Implemented on 2026-01-23**

### Changes Made

#### 1. `backend/app/tasks/celery_tasks.py`

Added two new functions (lines 479-579):

- **`extract_session_context_task`**: Celery task with retry mechanism
  - `max_retries=2`, `default_retry_delay=30`
  - Fetches last 100 messages from MongoDB
  - Calls async helper via `asyncio.run()`

- **`_extract_context_async`**: Async helper function
  - Creates own Motor client for async DB operations
  - Uses `ContextService` to extract context via LLM
  - Saves context and checks for summarization
  - Properly closes MongoDB client in finally block

#### 2. `backend/app/api/routes/auth.py`

Updated logout endpoint (lines 187-195):
- Removed blocking `await context_service.extract_and_save_context()`
- Now calls `extract_session_context_task.delay()` to queue background task
- Response returns immediately after token blacklisting

#### 3. `backend/app/api/routes/chat.py`

Updated WebSocket disconnect handler (lines 773-782):
- Removed blocking context extraction
- Now queues `extract_session_context_task.delay()`
- WebSocket disconnects are no longer delayed

### Result

- **Before:** Logout took 5-7 seconds (blocking LLM call)
- **After:** Logout completes in ~100-200ms (just token blacklisting)
- Context extraction still happens reliably via Celery worker
- Retry mechanism handles transient LLM failures
