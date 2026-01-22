# Bug Report: Chat Messages Not Isolated By User

**Status: FIXED**

## Summary

When a new user is created, they can see chat messages from previous users. Chat history should be unique per user but is currently being shared or leaked across user accounts.

## Severity

**Critical** - This is a data privacy/security issue.

## Steps to Reproduce

1. Login as User A
2. Send some chat messages to AI Coach
3. Logout
4. Create a new user (User B)
5. Login as User B
6. Open chat - **User A's chat messages are visible**

## Expected Behavior

- Each user should only see their own chat messages
- New users should see an empty chat history
- Chat messages should be filtered by `user_id`

## Actual Behavior

- New users see chat messages from other users
- Chat history appears to be shared across all users

## Root Cause Analysis

Possible causes to investigate:

### 1. Missing `user_id` filter in chat queries

Check `backend/app/api/routes/chat.py` - the query fetching chat history may not be filtering by `user_id`.

### 2. WebSocket connection not scoped to user

The WebSocket manager may be returning cached messages from previous connections without checking user ownership.

### 3. Frontend caching issue

The frontend chat store may be persisting messages in localStorage/sessionStorage without clearing on logout or checking user ID.

### 4. Database query missing user filter

```python
# BAD - fetches all messages
messages = await db.chat_messages.find().to_list()

# GOOD - fetches only current user's messages
messages = await db.chat_messages.find({"user_id": ObjectId(user_id)}).to_list()
```

## Files to Investigate

| File | What to Check |
|------|---------------|
| `backend/app/api/routes/chat.py` | Message query filters |
| `backend/app/core/websocket_manager.py` | Connection/message isolation |
| `frontend/src/stores/chatStore.ts` | State clearing on logout |
| `frontend/src/hooks/useWebSocket.ts` | Message handling per user |
| `backend/app/api/routes/auth.py` | Chat state reset on logout |

## Suggested Fix

1. Ensure all chat message queries include `user_id` filter
2. Clear frontend chat store on logout
3. Clear frontend chat store on login (before loading new user's messages)
4. Add `user_id` index to `chat_messages` collection if not present
5. Verify WebSocket connections are properly scoped per user

## Priority

**P0** - Fix immediately. This is a privacy violation.

## Labels

`bug`, `security`, `privacy`, `critical`, `chat`

---

## Resolution

**Fixed on 2026-01-21**

### Root Causes Identified

1. **Chat store not cleared on logout** - `useAuth.ts` logout function only cleared auth state, not chat messages
2. **Query cache not user-scoped** - React Query cache key `['chat', 'history']` didn't include user ID, causing stale data to persist across user sessions
3. **Conditional load prevented new data** - `messages.length === 0` check failed because old messages were still in store

### Files Modified

| File | Change |
|------|--------|
| `frontend/src/hooks/useAuth.ts` | Added `clearMessages()` and `queryClient.removeQueries({ queryKey: ['chat'] })` on logout |
| `frontend/src/components/chat/ChatContainer.tsx` | Added user ID to query key `['chat', 'history', user?.id]` and added user change detection to clear messages |

### Verification Steps

1. Login as User A, send messages
2. Logout
3. Create new User B or login as different user
4. Verify chat is empty and shows User B's history only
