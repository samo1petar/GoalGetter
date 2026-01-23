# Bug Report: Multiple Welcome Messages on Page Navigation

**Status: FIXED**

## Summary

When a user navigates away from the workspace page (to Goals or Meetings page) and returns, a new welcome message is displayed each time. The welcome message should only appear once per session (on initial login), not on every page navigation.

## Severity

**Medium** - This is a UX issue that creates a confusing experience and adds duplicate messages to the chat history.

## Steps to Reproduce

1. Login to GoalGetter
2. Observe the welcome message appears in the chat (correct)
3. Navigate to the Goals page (`/app/goals`)
4. Navigate back to the Workspace page (`/app`)
5. **BUG: Another welcome message appears**
6. Navigate to the Meetings page (`/app/meetings`)
7. Navigate back to the Workspace page (`/app`)
8. **BUG: Yet another welcome message appears**

## Expected Behavior

- Welcome message should appear only once when the user first logs in
- Navigating between pages within the app should NOT trigger new welcome messages
- The WebSocket connection should recognize it's a reconnection, not a fresh login

## Actual Behavior

- Each time the user returns to the Workspace page, a new welcome message is generated and displayed
- This creates multiple welcome messages in the chat history
- The backend receives `is_login=true` on each reconnection because the frontend doesn't persist the "first connection" state

## Root Cause Analysis

### Problem Location

The issue is in `frontend/src/lib/websocket/WebSocketClient.ts`:

```typescript
// Line 23 - Instance variable resets for each new WebSocketClient
private isFirstConnection = true;

// Line 38-39 - Sends is_login=true on first connection of THIS instance
const isLogin = this.isFirstConnection;
const wsUrl = `${this.url}?token=${encodeURIComponent(this.token)}&is_login=${isLogin}`;
```

### Flow Analysis

1. User logs in, lands on `/app` (Workspace)
2. `ChatContainer` mounts, `useWebSocket` hook runs
3. A new `WebSocketClient` is created with `isFirstConnection = true`
4. WebSocket connects with `is_login=true`, backend sends welcome message
5. `isFirstConnection` is set to `false`

6. User navigates to `/app/goals`
7. `ChatContainer` unmounts, WebSocket disconnects, `WebSocketClient` is destroyed

8. User navigates back to `/app`
9. `ChatContainer` mounts again, `useWebSocket` hook runs
10. A **NEW** `WebSocketClient` is created with `isFirstConnection = true` (reset!)
11. WebSocket connects with `is_login=true` again
12. Backend sends another welcome message

### Why This Happens

- The `isFirstConnection` flag is an instance variable on `WebSocketClient`
- When the component unmounts, the `WebSocketClient` instance is garbage collected
- When the component remounts, a brand new instance is created with all defaults reset
- There's no persistence of "already received welcome message this session" state

## Files Involved

| File | Issue |
|------|-------|
| `frontend/src/lib/websocket/WebSocketClient.ts` | `isFirstConnection` is instance-scoped, resets on new instance |
| `frontend/src/hooks/useWebSocket.ts` | Creates new `WebSocketClient` on each mount (via useEffect) |
| `frontend/src/stores/chatStore.ts` | Could store "welcomeReceived" flag but doesn't |
| `backend/app/api/routes/chat.py` | Backend correctly respects `is_login` param, no change needed |

## Suggested Fix

### Option 1: Use Module-Level Variable (Simple)

Store `isFirstConnection` at module level so it persists across instances:

```typescript
// At module level, outside the class
let hasConnectedThisSession = false;

export class WebSocketClient {
  connect(): void {
    // Use module-level flag instead of instance flag
    const isLogin = !hasConnectedThisSession;
    const wsUrl = `${this.url}?token=${encodeURIComponent(this.token)}&is_login=${isLogin}`;
    // ... rest of connection code

    // On successful connection:
    hasConnectedThisSession = true;
  }
}
```

### Option 2: Use Zustand Store (More Robust)

Add a `welcomeReceived` flag to `chatStore` that persists across component mounts:

```typescript
// In chatStore.ts
interface ChatState {
  // ... existing state
  welcomeReceivedThisSession: boolean;
  setWelcomeReceived: () => void;
}

// In useWebSocket.ts or WebSocketClient
// Only send is_login=true if !welcomeReceivedThisSession
```

### Option 3: Use sessionStorage (Persists Page Refreshes)

```typescript
const isLogin = !sessionStorage.getItem('goalGetterWelcomeShown');
// After showing welcome:
sessionStorage.setItem('goalGetterWelcomeShown', 'true');
// Clear on logout
```

## Recommended Fix

**Option 1 (Module-Level Variable)** is recommended because:
- Simplest implementation
- Doesn't persist across page refreshes (appropriate - new page load = new session)
- No additional dependencies on stores or browser storage
- Minimal code change

## Priority

**P2** - Should be fixed soon as it affects user experience and creates data clutter in chat history.

## Labels

`bug`, `ux`, `websocket`, `chat`, `welcome-message`

---

## Resolution

**Fixed on 2026-01-23**

### Implementation

Applied **Option 1 (Module-Level Variable)** as recommended.

### Changes Made to `frontend/src/lib/websocket/WebSocketClient.ts`

1. **Added module-level flag** (lines 6-9):
```typescript
// Module-level flag to track if we've connected this session.
// This persists across WebSocketClient instances so that navigation
// between pages doesn't reset it and trigger multiple welcome messages.
let hasConnectedThisSession = false;
```

2. **Removed instance variable** `isFirstConnection` - no longer needed

3. **Updated connect() method** (lines 41-44):
```typescript
// Only send is_login=true on first connection of the session, not on
// reconnections or when navigating between pages. The module-level
// hasConnectedThisSession flag persists across WebSocketClient instances.
const isLogin = !hasConnectedThisSession;
```

4. **Updated onopen handler** (lines 50-52):
```typescript
// Mark that we've connected this session so subsequent connections
// (from page navigation or reconnects) won't trigger welcome messages
hasConnectedThisSession = true;
```

### Verification Steps

1. Login to GoalGetter
2. Observe welcome message appears once
3. Navigate to Goals page
4. Navigate back to Workspace
5. Verify NO new welcome message appears
6. Navigate to Meetings page
7. Navigate back to Workspace
8. Verify NO new welcome message appears
