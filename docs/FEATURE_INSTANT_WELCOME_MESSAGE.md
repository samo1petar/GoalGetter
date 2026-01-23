# Feature Request: Instant Welcome Message with AI Follow-up

**Status: IMPLEMENTED**

## Overview

Make login feel instant for returning users by sending a quick static welcome message immediately, then generating a personalized AI summary as a follow-up message in the background.

## Problem

Currently, returning users experience a 2-4 second delay during login because the WebSocket connection waits for the AI-generated welcome message before sending the "connected" status. See `docs/INVESTIGATION_SLOW_LOGIN.md` for full analysis.

## Solution

Split the welcome into two messages:
1. **Instant static message** - Sent immediately, no LLM call
2. **AI-generated summary** - Generated in background, sent as follow-up

## User Experience

### Before (Current - Slow)
```
[Login] → [Connecting... 2-4 sec] → [Connected] → [AI Welcome]
```

### After (New - Instant)
```
[Login] → [Connected instantly] → [Quick Welcome] → [2-4 sec] → [AI Summary]
```

### What User Sees

**Message 1 (instant):**
> Welcome back! Let me check on your progress...

**Message 2 (2-4 seconds later):**
> Great to see you again! Last session you made progress on your **Learn TypeScript** goal...
>
> **Your Active Goals:**
> - Learn TypeScript (40% complete)
> ...

## Implementation

### 1. Update WebSocket Handler

**File:** `backend/app/api/routes/chat.py`

Find the welcome message generation section (around lines 455-490) and restructure it:

#### Current Code (lines 455-490):
```python
# Generate welcome message for the user (first-time or returning)
welcome_service = get_welcome_service(db)
welcome_data = await welcome_service.generate_welcome_message(user_id, is_login=is_login)

# Send connected confirmation
connected_message = {
    "type": "connected",
    ...
}
await websocket.send_json(connected_message)

# Send and save the welcome message as the first assistant message
welcome_message_content = welcome_data.get("message")
if welcome_message_content:
    # Save welcome message to database
    welcome_message_doc = MessageModel.create_message_document(...)
    ...
```

#### New Code:
```python
# Send connected confirmation IMMEDIATELY (don't wait for welcome generation)
welcome_service = get_welcome_service(db)

# Quick check if first-time user (fast - just DB queries)
is_first_time = await welcome_service.check_is_first_time_user(user_id)

connected_message = {
    "type": "connected",
    "content": "Connected to GoalGetter AI Coach",
    "user_phase": user_phase,
    "meeting_id": access.get("meeting_id"),
    "session_id": session_id,
    "has_context": not is_first_time,
    "is_first_time": is_first_time,
}
await websocket.send_json(connected_message)

# Handle welcome message based on user type
if is_login:
    if is_first_time:
        # First-time users: Send the full onboarding message (static, no LLM)
        welcome_data = await welcome_service.generate_welcome_message(user_id, is_login=True)
        welcome_message_content = welcome_data.get("message")
        if welcome_message_content:
            welcome_message_doc = MessageModel.create_message_document(
                user_id=user_id,
                role="assistant",
                content=welcome_message_content,
                meeting_id=access.get("meeting_id"),
            )
            result = await db.chat_messages.insert_one(welcome_message_doc)
            await websocket.send_json({
                "type": "welcome",
                "content": welcome_message_content,
                "message_id": str(result.inserted_id),
                "is_first_time": True,
                "has_context": False,
            })
    else:
        # Returning users: Send quick static message immediately
        quick_welcome = "Welcome back! Let me check on your progress..."
        quick_welcome_doc = MessageModel.create_message_document(
            user_id=user_id,
            role="assistant",
            content=quick_welcome,
            meeting_id=access.get("meeting_id"),
        )
        quick_result = await db.chat_messages.insert_one(quick_welcome_doc)
        await websocket.send_json({
            "type": "welcome",
            "content": quick_welcome,
            "message_id": str(quick_result.inserted_id),
            "is_first_time": False,
            "has_context": True,
        })

        # Generate detailed AI summary in background and send as follow-up
        async def send_ai_summary():
            try:
                summary_data = await welcome_service.generate_returning_user_summary(user_id)
                summary_content = summary_data.get("message")
                if summary_content:
                    # Save to database
                    summary_doc = MessageModel.create_message_document(
                        user_id=user_id,
                        role="assistant",
                        content=summary_content,
                        meeting_id=access.get("meeting_id"),
                    )
                    summary_result = await db.chat_messages.insert_one(summary_doc)

                    # Send to client
                    await websocket.send_json({
                        "type": "message",
                        "role": "assistant",
                        "content": summary_content,
                        "message_id": str(summary_result.inserted_id),
                        "timestamp": summary_doc["timestamp"].isoformat(),
                    })
            except Exception as e:
                logger.warning(f"Failed to generate AI summary for user {user_id}: {e}")

        asyncio.create_task(send_ai_summary())
```

### 2. Add Helper Method to WelcomeService

**File:** `backend/app/services/welcome_service.py`

Add a new method that generates ONLY the returning user summary (skipping the first-time check since we already know they're returning):

```python
async def generate_returning_user_summary(
    self,
    user_id: str,
) -> Dict[str, Any]:
    """
    Generate a personalized summary for a returning user.

    This is called asynchronously after the quick welcome is sent.
    Skips the first-time user check since caller already verified.

    Args:
        user_id: The user's ID

    Returns:
        Dict with 'message' containing the AI-generated summary
    """
    return await self._generate_returning_user_welcome(user_id)
```

### 3. Add Import for asyncio

**File:** `backend/app/api/routes/chat.py`

Ensure `asyncio` is imported at the top of the file:
```python
import asyncio
```

## Implementation Checklist

- [x] Add `import asyncio` to chat.py (if not present)
- [x] Send "connected" message immediately (before welcome generation)
- [x] Check if first-time user (fast DB query only)
- [x] For first-time users: Send static onboarding message (existing behavior)
- [x] For returning users: Send quick static welcome immediately
- [x] For returning users: Generate AI summary in background with `asyncio.create_task()`
- [x] Add `generate_returning_user_summary()` method to WelcomeService
- [ ] Test first-time user flow still works
- [ ] Test returning user gets instant welcome + AI follow-up

## Files to Modify

| File | Changes |
|------|---------|
| `backend/app/api/routes/chat.py` | Restructure welcome flow, add async background task |
| `backend/app/services/welcome_service.py` | Add `generate_returning_user_summary()` method |

## Testing

### First-Time User
1. Create new account
2. Login → Should see instant "connected"
3. Should see onboarding message immediately (static, no delay)

### Returning User
1. Login with existing account that has chat history
2. Should see instant "connected"
3. Should see "Welcome back! Let me check on your progress..." immediately
4. 2-4 seconds later, should see personalized AI summary with goals/progress

## Edge Cases

- **User sends message before AI summary arrives**: Should work fine - messages are independent
- **AI summary generation fails**: Logged as warning, user still has the quick welcome
- **WebSocket disconnects before summary sent**: Task fails silently, no impact

## Notes

- The quick welcome message IS saved to the database (so it appears in chat history)
- The AI summary IS saved to the database (as a separate message)
- Both messages have the "assistant" role
- First message uses type "welcome", second uses type "message"

## Priority

**P2** - Improves returning user login experience from 2-4 seconds to instant

---

## Resolution

**Implemented on 2026-01-23**

### Changes Made

#### 1. `backend/app/api/routes/chat.py`

- Added `import asyncio` at line 5
- Restructured welcome flow (lines 456-538):
  - "connected" message now sent IMMEDIATELY after connection
  - Quick `check_is_first_time_user()` determines user type
  - First-time users: Static onboarding sent immediately (no change in speed)
  - Returning users: Quick static welcome sent immediately
  - Returning users: AI summary generated via `asyncio.create_task()` and sent as follow-up

#### 2. `backend/app/services/welcome_service.py`

- Added `generate_returning_user_summary()` method (lines 296-312)
- Provides clean public API for background task
- Delegates to existing `_generate_returning_user_welcome()` method

### Result

| User Type | Before | After |
|-----------|--------|-------|
| First-time | ~500ms | ~500ms (unchanged) |
| Returning | 2-4 seconds | Instant + AI follow-up 2-4s later |

### User Experience (Returning Users)

**Message 1 (instant):**
> Welcome back! Let me check on your progress...

**Message 2 (2-4 seconds later):**
> [Personalized AI summary with goals, progress, action items]
