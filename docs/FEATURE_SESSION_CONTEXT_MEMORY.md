# Feature Request: Session Context Memory for AI Coach

## Summary

Implement persistent context memory that allows AI Coach to remember user progress across sessions. On each login, AI Coach provides a brief progress summary based on accumulated context from previous sessions.

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     SESSION LIFECYCLE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [Login] ──► [Load Context] ──► [AI Summary] ──► [Chat Session] │
│                                                                 │
│  [Chat Session] ──► [Extract Context] ──► [Save] ──► [Logout]   │
│                                                                 │
│  Context accumulates across sessions with rolling summarization │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## User Flow

### First-Time User
1. User logs in for the first time
2. No existing context → AI Coach greets normally without summary
3. Session begins, interactions tracked
4. On logout → context extracted and saved

### Returning User
1. User logs in
2. System loads accumulated context
3. AI Coach's first message includes brief progress summary:
   > "Welcome back! Last time we worked on your 'Learn TypeScript' goal - you completed 2 milestones and set a deadline for the coding project. You also started planning your fitness routine. Ready to continue?"
4. Session continues with full context awareness

## Context Data Structure

### Session Context Entry

```typescript
interface SessionContext {
  id: string;
  user_id: string;
  session_id: string;
  created_at: DateTime;
  ended_at: DateTime;

  // Extracted context as bullet points
  context_points: ContextPoint[];

  // Metadata
  message_count: number;
  goals_created: number;
  goals_updated: number;
  goals_completed: number;

  // Flag for summarized contexts
  is_summary: boolean;
  summarized_session_ids?: string[];  // If this is a summary of multiple sessions
}

interface ContextPoint {
  type: 'goal_progress' | 'decision' | 'action_item' | 'insight' | 'preference';
  content: string;
  related_goal_id?: string;
  timestamp: DateTime;
}
```

### Example Context Points

```json
{
  "context_points": [
    {
      "type": "goal_progress",
      "content": "Completed milestone 'Read Chapter 1-3' for 'Learn TypeScript' goal",
      "related_goal_id": "507f1f77bcf86cd799439011",
      "timestamp": "2026-01-20T14:30:00Z"
    },
    {
      "type": "decision",
      "content": "User decided to focus on backend development before frontend",
      "timestamp": "2026-01-20T14:45:00Z"
    },
    {
      "type": "action_item",
      "content": "Schedule 2 hours daily for coding practice",
      "timestamp": "2026-01-20T15:00:00Z"
    },
    {
      "type": "insight",
      "content": "User prefers morning sessions for deep work",
      "timestamp": "2026-01-20T15:10:00Z"
    }
  ]
}
```

## Context Extraction

### What to Extract

AI Coach determines what's important to remember, including:

| Type | Examples |
|------|----------|
| **Goal Progress** | Goals created, updated, completed; milestones reached; deadlines set |
| **Key Decisions** | User choices about priorities, approaches, focus areas |
| **Action Items** | Commitments user made, tasks they plan to do |
| **Insights** | User preferences, working style, motivations discovered |
| **Blockers** | Challenges discussed, obstacles identified |

### Extraction Triggers

Context is extracted and saved on:

1. **Explicit Logout** - User clicks logout button
2. **Session End** - Session timeout or browser close detected
3. **Periodic Save** - Every ~1000 messages during long sessions (prevents data loss)

### Extraction Process

```python
async def extract_session_context(
    user_id: str,
    session_id: str,
    conversation_history: List[Message]
) -> SessionContext:
    """
    Use AI to extract meaningful context points from conversation.
    """

    extraction_prompt = """
    Analyze this conversation and extract key points to remember for future sessions.

    Extract:
    - Goal progress (what was accomplished, updated, or planned)
    - Key decisions the user made
    - Action items or commitments
    - Insights about user preferences or working style
    - Any blockers or challenges discussed

    Format as bullet points, each categorized by type.
    Be concise but capture the essential information.
    """

    # Call AI to extract context
    context_points = await ai_extract_context(
        conversation_history,
        extraction_prompt
    )

    return SessionContext(
        user_id=user_id,
        session_id=session_id,
        context_points=context_points,
        # ... metadata
    )
```

## Context Storage

### Database Schema

```python
# MongoDB Collection: session_contexts

{
    "_id": ObjectId,
    "user_id": ObjectId,
    "session_id": str,
    "created_at": DateTime,
    "ended_at": DateTime,
    "context_points": [
        {
            "type": str,
            "content": str,
            "related_goal_id": Optional[ObjectId],
            "timestamp": DateTime
        }
    ],
    "message_count": int,
    "goals_created": int,
    "goals_updated": int,
    "goals_completed": int,
    "is_summary": bool,
    "summarized_session_ids": Optional[List[str]]
}

# Index for efficient queries
db.session_contexts.createIndex({ "user_id": 1, "created_at": -1 })
```

## Rolling Summarization

### Strategy

To prevent unbounded context growth, older sessions are periodically summarized:

```
Sessions 1-10  ──► Summary A (after 20 total sessions)
Sessions 11-20 ──► Summary B (after 30 total sessions)
Sessions 21-30 ──► Summary C (after 40 total sessions)
...and so on
```

### Summarization Logic

```python
async def maybe_summarize_old_sessions(user_id: str) -> None:
    """
    Check if summarization is needed and perform it.

    Rule: After every 10 new unsummarized sessions beyond 10,
    summarize the oldest 10 unsummarized sessions.
    """

    unsummarized = await get_unsummarized_sessions(user_id)

    if len(unsummarized) >= 20:
        # Get oldest 10 unsummarized sessions
        to_summarize = unsummarized[:10]

        # Create summary context
        summary = await create_session_summary(to_summarize)

        # Save summary
        await save_session_context(summary)

        # Mark original sessions as summarized (or delete)
        await mark_sessions_summarized(to_summarize)
```

### Summary Format

```python
async def create_session_summary(sessions: List[SessionContext]) -> SessionContext:
    """
    Combine multiple session contexts into a single summary.
    """

    date_range = f"{sessions[0].created_at} to {sessions[-1].ended_at}"

    summarization_prompt = f"""
    Summarize these {len(sessions)} session contexts into a concise summary.
    Date range: {date_range}

    Combine similar points, remove redundancy, keep the most important:
    - Major goal achievements
    - Significant decisions
    - Ongoing action items (not completed ones)
    - Key user preferences discovered

    Be concise but comprehensive.
    """

    combined_points = await ai_summarize_contexts(sessions, summarization_prompt)

    return SessionContext(
        is_summary=True,
        summarized_session_ids=[s.session_id for s in sessions],
        context_points=combined_points,
        # ... metadata
    )
```

## Login Summary Generation

### Loading Context

```python
async def load_user_context(user_id: str) -> List[SessionContext]:
    """
    Load all relevant context for a user (summaries + recent sessions).
    """

    # Get all summaries
    summaries = await db.session_contexts.find({
        "user_id": user_id,
        "is_summary": True
    }).sort("created_at", 1).to_list()

    # Get recent unsummarized sessions
    recent = await db.session_contexts.find({
        "user_id": user_id,
        "is_summary": False
    }).sort("created_at", -1).limit(10).to_list()

    return summaries + recent
```

### Generating Welcome Summary

```python
async def generate_welcome_summary(user_id: str) -> Optional[str]:
    """
    Generate AI Coach's opening summary message for returning user.
    """

    contexts = await load_user_context(user_id)

    if not contexts:
        return None  # First-time user, no summary needed

    # Get current goals for reference
    current_goals = await get_user_goals(user_id)

    summary_prompt = """
    Generate a brief, warm welcome message summarizing the user's progress.

    Include:
    - What they worked on recently
    - Any achievements or milestones
    - Pending action items or next steps
    - Encouragement to continue

    Keep it to 2-3 sentences. Be conversational and supportive.
    Don't overwhelm - just the highlights.
    """

    return await ai_generate_summary(contexts, current_goals, summary_prompt)
```

### Example Welcome Messages

**After productive session:**
> "Welcome back! Last session you made great progress on your 'Launch Side Project' goal - you defined all 5 milestones and completed the market research. You mentioned wanting to start wireframing next. Ready to dive in?"

**After planning session:**
> "Good to see you again! We spent last time setting up your Q1 goals and you decided to prioritize learning Rust before the web development project. You also committed to 1 hour of daily practice. How's that going?"

**After multiple sessions (with summary):**
> "Welcome back! Over the past few weeks, you've completed 3 goals and made solid progress on 'Write Technical Blog'. Last time you finished the outline and set a publishing deadline for February. Shall we work on the first draft today?"

## Implementation Plan

### Phase 1: Data Model & Storage

1. Create `SessionContext` model
2. Add MongoDB collection and indexes
3. Create CRUD operations for session contexts

### Phase 2: Context Extraction

1. Implement extraction trigger on logout
2. Implement session-end detection (WebSocket disconnect)
3. Implement periodic save (message count threshold)
4. Create AI extraction prompt and handler

### Phase 3: Welcome Summary

1. Implement context loading on login
2. Create welcome summary generation
3. Integrate with chat initialization
4. Handle first-time user case

### Phase 4: Rolling Summarization

1. Implement summarization check after each session save
2. Create AI summarization prompt and handler
3. Implement session cleanup/marking

## Files to Create/Modify

### New Files

| File | Purpose |
|------|---------|
| `backend/app/models/session_context.py` | SessionContext model |
| `backend/app/services/context_service.py` | Context extraction, storage, summarization |
| `backend/app/services/welcome_service.py` | Welcome summary generation |

### Modified Files

| File | Changes |
|------|---------|
| `backend/app/api/routes/chat.py` | Add context extraction triggers, welcome summary |
| `backend/app/api/routes/auth.py` | Trigger context save on logout |
| `backend/app/core/websocket.py` | Detect session end, periodic saves |
| `frontend/src/hooks/useWebSocket.ts` | Handle welcome summary message |
| `frontend/src/components/chat/ChatContainer.tsx` | Display welcome summary |

## API Endpoints

```python
# New endpoints

GET  /api/v1/context/summary
# Returns welcome summary for current user (called on login/chat init)

POST /api/v1/context/extract
# Manually trigger context extraction (for explicit logout)

GET  /api/v1/context/history
# Get user's context history (for debugging/admin)
```

## Acceptance Criteria

- [ ] Context extracted on explicit logout
- [ ] Context extracted on session end (WebSocket disconnect)
- [ ] Context extracted periodically (every ~1000 messages)
- [ ] First-time users see normal greeting (no summary)
- [ ] Returning users see brief progress summary
- [ ] Summary includes recent goal progress, decisions, action items
- [ ] Rolling summarization works (10 sessions → 1 summary after threshold)
- [ ] Context persists across browser sessions
- [ ] Performance acceptable (summary generation < 3 seconds)

## Edge Cases

1. **Very short session** - User logs in and immediately logs out → minimal/no context to extract
2. **No meaningful interactions** - User only browsed, no goals discussed → skip extraction
3. **Concurrent sessions** - User logged in on multiple devices → handle gracefully
4. **Context extraction fails** - AI fails to extract → log error, don't block logout
5. **Very long history** - User with years of data → ensure summarization keeps it manageable

## Privacy Considerations

- Context data should be deletable (GDPR compliance)
- Add "Clear my history" option in settings
- Context should not include sensitive information user hasn't shared with goals

## Priority

Medium-High - Enhances user experience and AI Coach value

## Labels

`feature`, `ai-coach`, `context`, `memory`, `personalization`
