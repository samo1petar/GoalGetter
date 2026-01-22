# Feature: Fresh Chat with Context-Aware Welcome

## Summary

On each login, users see a fresh chat (no old messages) with a personalized welcome from AI Coach. Returning users get a progress summary based on prior sessions. First-time users receive an onboarding guide explaining the tool.

## Current Behavior

- Chat history is loaded and displayed from previous sessions
- Users see all past messages on login
- No distinction between first-time and returning users

## Desired Behavior

```
┌─────────────────────────────────────────────────────────────────┐
│                      LOGIN FLOW                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [Login] ──► [Check User Context] ──► [Generate Welcome]        │
│                     │                                            │
│                     ├── First-time user ──► Onboarding Guide    │
│                     │                                            │
│                     └── Returning user ──► Progress Summary     │
│                                                                  │
│  Chat starts FRESH - no old messages loaded                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## User Experience

### First-Time User

When a user logs in for the first time (no prior chat history or context):

```
┌─────────────────────────────────────────────────────────────┐
│  Alfred - AI Coach                              ● Connected │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🎯 Welcome to GoalGetter!                                  │
│                                                             │
│  I'm Alfred, your AI Coach. I'm here to help you set,      │
│  track, and achieve your goals. Here's how we can work     │
│  together:                                                  │
│                                                             │
│  • **Set Goals** - Tell me what you want to achieve and    │
│    I'll help you create structured, actionable goals       │
│                                                             │
│  • **Track Progress** - Share your updates and I'll help   │
│    you stay accountable and motivated                      │
│                                                             │
│  • **Get Guidance** - Ask me for advice, strategies, or    │
│    help breaking down complex goals                        │
│                                                             │
│  Ready to get started? Tell me about a goal you'd like     │
│  to work on, or ask me anything!                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Returning User

When a user logs in with prior context:

```
┌─────────────────────────────────────────────────────────────┐
│  Alfred - AI Coach                              ● Connected │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Welcome back! Here's where we left off:                    │
│                                                             │
│  📊 **Your Progress**                                       │
│  • You've been working on "Learn TypeScript" - completed   │
│    2 out of 5 milestones                                   │
│  • Last session we discussed breaking down the "Build      │
│    Portfolio" project into smaller tasks                   │
│  • You committed to 1 hour of daily coding practice        │
│                                                             │
│  🎯 **Active Goals**                                        │
│  • Learn TypeScript (40% complete)                         │
│  • Build Portfolio Website (planning phase)                │
│                                                             │
│  What would you like to focus on today?                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Technical Approach

### 1. Don't Load Chat History on Login

Currently in `ChatContainer.tsx`:
```typescript
// CURRENT - loads old messages
const { data: historyData } = useQuery({
  queryKey: ['chat', 'history', user?.id],
  queryFn: () => chatApi.getHistory({ page_size: 50 }),
});
```

Change to:
```typescript
// NEW - don't load history, start fresh
// Remove the history query entirely
// Chat starts empty, AI Coach sends welcome message
```

### 2. AI Coach Sends Welcome as First Message

When WebSocket connects, AI Coach should automatically send a welcome message based on user context. This happens server-side.

**Flow:**
1. User connects via WebSocket
2. Server checks if user has prior context (session_contexts collection)
3. Server generates appropriate welcome message:
   - No context → First-time user onboarding
   - Has context → Progress summary
4. Server sends welcome message as first assistant message
5. Message is saved to chat_messages for this session

### 3. Welcome Message Generation

#### First-Time User Detection

```python
async def is_first_time_user(user_id: str) -> bool:
    """Check if user has any prior context or chat history."""
    context_count = await db.session_contexts.count_documents({"user_id": user_id})
    message_count = await db.chat_messages.count_documents({"user_id": user_id})
    return context_count == 0 and message_count == 0
```

#### Onboarding Message (First-Time)

Static or semi-static welcome message introducing the tool:
- What AI Coach can do
- How to set goals
- How to track progress
- Invitation to start

#### Progress Summary (Returning User)

Use existing `WelcomeService.generate_welcome_summary()` but enhance it to:
- Include active goals and their status
- Summarize recent progress from context points
- Mention any pending action items
- Provide a natural conversation opener

### 4. Data Sources for Summary

| Data | Source | Purpose |
|------|--------|---------|
| Prior discussions | `session_contexts` | What was discussed, decisions made |
| Active goals | `goals` collection | Current goal status, progress |
| Recent milestones | `goals.milestones` | Completed/upcoming milestones |
| Action items | `session_contexts.context_points` | Pending commitments |

### 5. Chat History Access

Old chat history should still be accessible but not shown by default:
- Add a "View Chat History" button/link in chat UI
- Opens a modal or side panel with paginated history
- Or simply accessible via a separate "History" page

## Files to Modify

### Backend

| File | Changes |
|------|---------|
| `backend/app/services/welcome_service.py` | Enhance to generate full welcome message (not just summary) |
| `backend/app/api/routes/chat.py` | Send welcome message on WebSocket connect |
| `backend/app/services/context_service.py` | Add first-time user detection |

### Frontend

| File | Changes |
|------|---------|
| `frontend/src/components/chat/ChatContainer.tsx` | Remove history loading, handle welcome message |
| `frontend/src/hooks/useWebSocket.ts` | Handle welcome message as first assistant message |

## Message Format

### WebSocket Welcome Message

```json
{
  "type": "welcome",
  "content": "Welcome back! Here's where we left off...",
  "is_first_time": false,
  "active_goals": [
    {"id": "...", "title": "Learn TypeScript", "progress": 40}
  ],
  "context_summary": {
    "recent_progress": ["Completed milestone X", "Discussed Y"],
    "pending_actions": ["1 hour daily practice"],
    "last_session": "2026-01-20"
  }
}
```

## Edge Cases

| Case | Handling |
|------|----------|
| User with goals but no chat history | Show goals summary, invite to chat |
| User with chat history but no context | Treat as returning user, show basic welcome |
| Very long context history | Summarize to most recent/relevant points |
| Context extraction failed previously | Fall back to goal-based summary |
| No goals and no context | First-time user experience |

## UI Considerations

1. **Welcome message styling** - Should look like an AI Coach message but perhaps with a subtle visual distinction (welcome banner style)

2. **Dismissible** - User should be able to dismiss/collapse the welcome after reading

3. **Action buttons** - Consider adding quick action buttons:
   - "Continue with [Goal Name]"
   - "Create New Goal"
   - "View All Goals"

4. **History access** - Clear way to access old conversations if needed

## Privacy Note

- Context summaries only include what the user discussed
- No cross-user data leakage (addressed in separate bug fixes)
- User can clear their context history via settings

## Success Metrics

- Users engage with chat faster (reduced time to first message)
- Higher goal completion rates (better context continuity)
- Positive user feedback on personalized experience

## Implementation Order

1. Add first-time user detection
2. Create onboarding message template
3. Enhance welcome summary generation
4. Modify WebSocket to send welcome on connect
5. Update frontend to not load history
6. Add welcome message handling in frontend
7. Add "View History" option for accessing old chats
