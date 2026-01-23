# Investigation: Slow Logout (5-7 seconds)

**Status: RESOLVED** - See `FEATURE_CELERY_CONTEXT_EXTRACTION.md` for the fix.

## Summary

**Root Cause: Context extraction blocks the logout HTTP response**

The logout endpoint performs synchronous (awaited) AI context extraction, which involves an LLM API call that takes 3-6 seconds. During this time, the user can still interact with the app, causing a confusing UX.

## Detailed Analysis

### The Logout Flow

```
User clicks "Logout"
    ↓
Frontend: useAuth.logout()
    ↓
Frontend: await authApi.logout()  ← WAITS HERE
    ↓
Backend: POST /api/v1/auth/logout
    ↓
Backend: Token blacklisting (~100ms)
    ↓
Backend: await extract_and_save_context()  ← BLOCKS 5-7 SECONDS
    ↓
Backend: Returns response
    ↓
Frontend: clearMessages(), logoutStore(), router.push('/login')
```

### Problem Location

**File:** `backend/app/api/routes/auth.py` (lines 188-200)

```python
# Extract and save session context for AI Coach memory
# This runs in the background and doesn't block the logout response  ← COMMENT IS WRONG!
try:
    context_service = get_context_service(db)
    session_id = jti or f"logout-{datetime.utcnow().timestamp()}"
    await context_service.extract_and_save_context(  ← BLOCKING AWAIT
        user_id=current_user["id"],
        session_id=session_id,
    )
```

**The comment says "runs in the background" but the code uses `await`, making it synchronous/blocking!**

### What `extract_and_save_context()` Does

**File:** `backend/app/services/context_service.py`

1. **Fetch conversation history** (~100-200ms)
   - Queries MongoDB for recent chat messages

2. **Build extraction prompt** (~10ms)
   - Formats messages into a prompt for the LLM

3. **LLM API call** (~3-6 seconds) ← THE SLOW PART
   - Sends the conversation to Claude/OpenAI
   - Asks it to extract key context points (goals, decisions, insights)
   - Waits for full response

4. **Parse JSON response** (~10ms)
   - Extracts structured data from LLM response

5. **Save to database** (~50-100ms)
   - Stores session context in MongoDB

6. **Maybe trigger summarization** (0 or +3-6 seconds)
   - If user has 20+ unsummarized sessions, triggers ANOTHER LLM call
   - This could add another 3-6 seconds in worst case

### Additional Finding: Double Context Extraction

Context extraction also happens on WebSocket disconnect:

**File:** `backend/app/api/routes/chat.py` (lines 773-789)

```python
finally:
    if user:
        # Extract and save session context on disconnect
        try:
            context_service = get_context_service(db)
            await context_service.extract_and_save_context(
                user_id=user_id,
                session_id=ws_session_id,
            )
```

This means if a user logs out while the WebSocket is connected, context extraction might happen **twice** - once on WebSocket disconnect and once on logout endpoint.

### Frontend Waiting Behavior

**File:** `frontend/src/hooks/useAuth.ts` (lines 76-93)

```typescript
const logout = useCallback(async () => {
    try {
      await authApi.logout();  // ← WAITS FOR BACKEND RESPONSE
    } catch {
      // Ignore errors on logout
    }
    // Only AFTER backend responds:
    clearMessages();
    queryClient.removeQueries({ ... });
    logoutStore();
    router.push('/login');
    toast.success('Logged out successfully');
}, [...]);
```

## Why This Is Bad UX

1. **User can still interact with the app** during the 5-7 second wait
2. **No loading indicator** - user doesn't know logout is in progress
3. **Changes made during wait are lost** - state cleared when logout completes
4. **Feels broken** - nothing seems to happen after clicking logout
5. **Potential data inconsistency** - if user modifies goals during wait

## Proposed Solutions

### Option 1: Fire-and-Forget with asyncio.create_task() (Recommended)

Simple change in the logout endpoint:

```python
import asyncio

# Don't await - fire and forget
asyncio.create_task(context_service.extract_and_save_context(
    user_id=current_user["id"],
    session_id=session_id,
))
```

**Pros:** Simple, immediate improvement
**Cons:** If server restarts, task might not complete

### Option 2: Remove Logout Context Extraction Entirely

Rely solely on WebSocket disconnect for context extraction (already happens in chat.py).

```python
# Remove lines 188-200 from auth.py entirely
```

**Pros:** Simplest solution, eliminates duplicate extraction
**Cons:** Context not extracted if user closes browser without WebSocket disconnect

### Option 3: Celery Background Task

Create a new Celery task for context extraction:

```python
# In celery_tasks.py
@shared_task(name="app.tasks.celery_tasks.extract_context_task")
def extract_context_task(user_id: str, session_id: str):
    # Run extraction synchronously in worker
    ...

# In auth.py logout endpoint
from app.tasks.celery_tasks import extract_context_task
extract_context_task.delay(current_user["id"], session_id)
```

**Pros:** Reliable, survives restarts, scalable
**Cons:** More complex, requires Celery worker running

### Option 4: Frontend Optimistic Logout

Don't wait for backend response:

```typescript
const logout = useCallback(async () => {
    // Fire request but don't wait
    authApi.logout().catch(() => {});

    // Immediately clear state and redirect
    clearMessages();
    logoutStore();
    router.push('/login');
}, [...]);
```

**Pros:** Instant UX improvement, no backend changes
**Cons:** Token might not get blacklisted if request fails

### Option 5: Hybrid Approach (Best)

Combine Options 1 and 4:
- Frontend: Don't wait for logout response
- Backend: Use fire-and-forget for context extraction

## Recommendation

**Implement Option 5 (Hybrid)** for best results:

1. **Backend change:** Use `asyncio.create_task()` instead of `await` for context extraction
2. **Frontend change:** Don't await the logout API call
3. **Consider:** Also removing the logout context extraction entirely since WebSocket disconnect already handles it

This gives:
- Instant logout UX
- Context still gets extracted (fire-and-forget)
- No duplicate extraction if we remove logout extraction

## Files to Modify

| File | Change |
|------|--------|
| `backend/app/api/routes/auth.py` | Use `asyncio.create_task()` or remove extraction |
| `frontend/src/hooks/useAuth.ts` | Don't await logout response |

## Priority

**P1** - This significantly impacts user experience on every logout.
