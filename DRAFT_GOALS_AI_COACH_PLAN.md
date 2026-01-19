# Plan: AI Coach Draft Goals Integration

## Overview

Two interconnected features:

1. **Read Access**: Enable the AI Coach to see draft goals that exist only on the frontend (not yet saved to the backend)
2. **Write Access**: Enable the AI Coach to create and edit goals directly through conversation, with changes appearing in the editor in real-time

## Current State

- **Backend**: Goals are stored in MongoDB with phases: `draft`, `active`, `completed`, `archived`
- **Chat Context**: `get_user_goals()` fetches saved goals (excluding archived) and injects them into Claude's system prompt
- **Frontend**: Goal editor auto-saves to backend with a 2-second debounce
- **Gap**: Unsaved changes in the editor are not visible to the AI Coach

## Proposed Solution

### Frontend Changes

1. **Create a draft goals context provider or hook** (`useDraftGoals`)
   - Track current editor content that hasn't been saved yet
   - Expose a function to get the current draft state

2. **Modify WebSocket message payload**
   - When sending a chat message, include current draft goals as metadata
   - Structure: `{ type: "message", content: "...", draft_goals: [...] }`

3. **Draft goal format**
   ```typescript
   interface DraftGoal {
     id?: string;           // undefined if new goal
     title: string;
     content: string;       // Current editor content (plain text or parsed from BlockNote)
     template_type: string;
   }
   ```

### Backend Changes

1. **Update WebSocket message handler** (`/backend/app/api/routes/chat.py`)
   - Parse `draft_goals` from incoming message payload
   - Merge with saved goals (draft goals override saved versions by ID)

2. **Update Claude service** (`/backend/app/services/claude_service.py`)
   - Accept optional `draft_goals` parameter in `stream_message()`
   - Modify `_build_system_prompt()` to include a "Draft Goals (Work in Progress)" section
   - Clearly label drafts so Claude knows they're incomplete

3. **System prompt format**
   ```
   CURRENT CONTEXT:
   User Phase: {user_phase}

   Saved Goals:
   {user_goals}

   Draft Goals (Work in Progress):
   {draft_goals}
   ```

## Implementation Steps

### Step 1: Frontend - Track Draft State
- [ ] Create `useDraftGoals` hook in `/frontend/src/hooks/`
- [ ] Store current unsaved editor content
- [ ] Parse BlockNote JSON to extract plain text summary

### Step 2: Frontend - Send Drafts with Messages
- [ ] Update `WebSocketClient` to accept draft goals in `sendMessage()`
- [ ] Modify chat input to include current drafts when sending

### Step 3: Backend - Receive and Process Drafts
- [ ] Update WebSocket handler to extract `draft_goals` from payload
- [ ] Add validation for draft goal structure

### Step 4: Backend - Inject into Prompt
- [ ] Update `_build_system_prompt()` with draft goals section
- [ ] Merge logic: drafts override saved goals with same ID

### Step 5: Testing
- [ ] Test with new unsaved goal
- [ ] Test with edits to existing goal
- [ ] Test with multiple drafts
- [ ] Verify Claude acknowledges draft content

## Files to Modify

| File | Changes |
|------|---------|
| `frontend/src/hooks/useDraftGoals.ts` | New hook (create) |
| `frontend/src/lib/websocket.ts` | Add draft_goals to message payload |
| `frontend/src/components/chat/ChatInput.tsx` | Include drafts when sending |
| `backend/app/api/routes/chat.py` | Parse draft_goals from WebSocket message |
| `backend/app/services/claude_service.py` | Update system prompt builder |

## Considerations

- **Privacy**: Draft content is sent over WebSocket (already authenticated)
- **Performance**: Only send drafts when they exist to minimize payload
- **UX**: Consider showing an indicator when drafts are being shared with coach

---

# Feature 2: AI Coach Goal Editing

## Overview

Allow the AI Coach to create and modify goals through natural conversation. When the user discusses their goals, the coach can directly populate or update the goal editor, creating a collaborative goal-writing experience.

## User Experience

**Example conversation:**
```
User: "I want to lose 20 pounds in the next 6 months"

Coach: "Great goal! Let me help you make it more actionable..."
[Coach creates a new goal in the editor with SMART structure]

User: "Can you add a milestone for the first month?"

Coach: "Absolutely, I'll add a milestone for losing the first 5 pounds..."
[Coach updates the goal with a new milestone]
```

The user sees the goal editor update in real-time as the coach "types" the goal.

## Technical Approach: Claude Tool Use

Use Claude's tool/function calling feature to give the AI Coach the ability to manipulate goals.

### Tools to Implement

#### 1. `create_goal`
Creates a new goal and opens it in the editor.

```json
{
  "name": "create_goal",
  "description": "Create a new goal for the user. Use this when the user expresses a new goal they want to achieve.",
  "input_schema": {
    "type": "object",
    "properties": {
      "title": {
        "type": "string",
        "description": "A clear, concise title for the goal"
      },
      "content": {
        "type": "string",
        "description": "Detailed goal description in markdown format"
      },
      "template_type": {
        "type": "string",
        "enum": ["smart", "okr", "custom"],
        "description": "The goal framework to use"
      },
      "deadline": {
        "type": "string",
        "description": "Target completion date (ISO 8601 format)"
      },
      "milestones": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "title": { "type": "string" },
            "description": { "type": "string" },
            "target_date": { "type": "string" }
          }
        },
        "description": "List of milestones to track progress"
      },
      "tags": {
        "type": "array",
        "items": { "type": "string" },
        "description": "Tags to categorize the goal"
      }
    },
    "required": ["title", "content"]
  }
}
```

#### 2. `update_goal`
Modifies an existing goal.

```json
{
  "name": "update_goal",
  "description": "Update an existing goal. Use this to refine, expand, or modify a goal the user is working on.",
  "input_schema": {
    "type": "object",
    "properties": {
      "goal_id": {
        "type": "string",
        "description": "ID of the goal to update (use 'current' for the active goal in editor)"
      },
      "title": {
        "type": "string",
        "description": "Updated title (optional)"
      },
      "content": {
        "type": "string",
        "description": "Updated content in markdown (optional)"
      },
      "deadline": {
        "type": "string",
        "description": "Updated deadline (optional)"
      },
      "milestones": {
        "type": "array",
        "description": "Replace all milestones with this list (optional)"
      },
      "add_milestone": {
        "type": "object",
        "description": "Add a single milestone without replacing existing ones"
      },
      "tags": {
        "type": "array",
        "description": "Updated tags (optional)"
      }
    },
    "required": ["goal_id"]
  }
}
```

#### 3. `set_goal_phase`
Changes a goal's phase (e.g., activate a draft).

```json
{
  "name": "set_goal_phase",
  "description": "Change a goal's phase. Use to activate a draft or mark a goal complete.",
  "input_schema": {
    "type": "object",
    "properties": {
      "goal_id": {
        "type": "string",
        "description": "ID of the goal (use 'current' for active goal)"
      },
      "phase": {
        "type": "string",
        "enum": ["draft", "active", "completed", "archived"],
        "description": "New phase for the goal"
      }
    },
    "required": ["goal_id", "phase"]
  }
}
```

## Architecture

### Message Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                  │
├──────────────────────────────────────────────────────────────────┤
│  User types message                                               │
│       │                                                           │
│       ▼                                                           │
│  WebSocket sends { type: "message", content: "...", drafts: [] } │
│       │                                                           │
└───────┼──────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────────────┐
│                         BACKEND                                   │
├──────────────────────────────────────────────────────────────────┤
│  WebSocket receives message                                       │
│       │                                                           │
│       ▼                                                           │
│  Claude API called with tools defined                             │
│       │                                                           │
│       ├─── Response only ──────► Stream text to frontend          │
│       │                                                           │
│       └─── Tool call ──────────► Process tool, execute action     │
│                                       │                           │
│                                       ▼                           │
│                               Send tool result to frontend        │
│                               via WebSocket                       │
│                                       │                           │
└───────────────────────────────────────┼──────────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                  │
├──────────────────────────────────────────────────────────────────┤
│  WebSocket receives { type: "tool_result", tool: "create_goal" } │
│       │                                                           │
│       ▼                                                           │
│  Goal store/editor updated                                        │
│       │                                                           │
│       ▼                                                           │
│  UI reflects changes (goal appears/updates in editor)             │
└──────────────────────────────────────────────────────────────────┘
```

### New WebSocket Message Types

**Backend to Frontend:**

```typescript
// Tool execution result
{
  type: "tool_call",
  tool: "create_goal" | "update_goal" | "set_goal_phase",
  result: {
    success: boolean,
    goal_id?: string,
    goal?: Goal,        // Full goal object for create/update
    error?: string
  }
}

// Streaming continues after tool execution
{
  type: "response_chunk",
  content: "I've created a new goal for you..."
}
```

**Frontend handling:**
```typescript
case 'tool_call':
  if (data.tool === 'create_goal' && data.result.success) {
    // Add goal to store
    goalStore.addGoal(data.result.goal);
    // Open in editor
    uiStore.setActiveGoalId(data.result.goal_id);
  }
  if (data.tool === 'update_goal' && data.result.success) {
    // Update goal in store (triggers editor refresh)
    goalStore.updateGoal(data.result.goal_id, data.result.goal);
  }
  break;
```

## Backend Implementation Details

### Claude Service Changes

**Tool definitions** added to Claude API call:

```python
# claude_service.py

GOAL_TOOLS = [
    {
        "name": "create_goal",
        "description": "Create a new goal for the user...",
        "input_schema": { ... }
    },
    {
        "name": "update_goal",
        "description": "Update an existing goal...",
        "input_schema": { ... }
    },
    {
        "name": "set_goal_phase",
        "description": "Change a goal's phase...",
        "input_schema": { ... }
    }
]

async def stream_message_with_tools(self, message, ..., tools=GOAL_TOOLS):
    response = await self.client.messages.create(
        model=self.model,
        messages=messages,
        system=system_prompt,
        tools=tools,
        stream=True
    )

    for event in response:
        if event.type == "content_block_start":
            if event.content_block.type == "tool_use":
                # Handle tool call
                yield {"type": "tool_call", "tool": event.content_block.name, ...}
        elif event.type == "content_block_delta":
            if event.delta.type == "text_delta":
                yield {"type": "text", "content": event.delta.text}
```

### Tool Execution Handler

```python
# chat.py or new tool_handler.py

async def execute_goal_tool(tool_name: str, tool_input: dict, user_id: str, db) -> dict:
    """Execute a goal manipulation tool and return result."""

    if tool_name == "create_goal":
        goal_doc = GoalModel.create_goal_document(
            user_id=user_id,
            title=tool_input["title"],
            content=tool_input["content"],
            template_type=tool_input.get("template_type", "custom"),
            # ... other fields
        )
        result = await db.goals.insert_one(goal_doc)
        goal_doc["_id"] = result.inserted_id
        return {
            "success": True,
            "goal_id": str(result.inserted_id),
            "goal": GoalModel.serialize_goal(goal_doc)
        }

    elif tool_name == "update_goal":
        goal_id = tool_input["goal_id"]
        # Handle "current" as active goal reference
        # Update fields that were provided
        # Return updated goal

    elif tool_name == "set_goal_phase":
        # Update phase
        # Return success
```

## Frontend Implementation Details

### Goal Store Updates

```typescript
// stores/goalStore.ts (new or extend existing)

interface GoalStore {
  goals: Goal[];
  activeGoalId: string | null;

  // New methods for AI Coach integration
  addGoalFromCoach: (goal: Goal) => void;
  updateGoalFromCoach: (goalId: string, updates: Partial<Goal>) => void;
  setActiveGoal: (goalId: string) => void;
}
```

### WebSocket Handler Updates

```typescript
// hooks/useWebSocket.ts

case 'tool_call':
  const { tool, result } = data;

  if (result.success) {
    switch (tool) {
      case 'create_goal':
        // Invalidate React Query cache to refetch goals
        queryClient.invalidateQueries(['goals']);
        // Set as active goal to show in editor
        uiStore.setActiveGoalId(result.goal_id);
        // Optional: Show toast notification
        toast.success('Goal created by AI Coach');
        break;

      case 'update_goal':
        queryClient.invalidateQueries(['goals']);
        queryClient.invalidateQueries(['goal', result.goal_id]);
        break;

      case 'set_goal_phase':
        queryClient.invalidateQueries(['goals']);
        break;
    }
  } else {
    console.error(`Tool ${tool} failed:`, result.error);
  }
  break;
```

### Editor Sync

The editor already uses React Query and auto-refreshes when the cache is invalidated. When a tool call updates a goal:

1. `queryClient.invalidateQueries(['goal', goalId])` triggers refetch
2. Editor's `useGoal(goalId)` hook receives new data
3. BlockNote editor updates content

**Consideration**: May need to handle editor focus/cursor position to avoid disrupting user if they're also typing.

## Implementation Steps

### Step 6: Backend - Define Tools
- [ ] Create tool schemas in `claude_service.py`
- [ ] Add tools to Claude API call

### Step 7: Backend - Tool Execution
- [ ] Create `execute_goal_tool()` handler
- [ ] Handle `create_goal` tool
- [ ] Handle `update_goal` tool
- [ ] Handle `set_goal_phase` tool

### Step 8: Backend - WebSocket Tool Messages
- [ ] Detect tool calls in streaming response
- [ ] Execute tool and get result
- [ ] Send `tool_call` message type to frontend
- [ ] Continue streaming Claude's response after tool execution

### Step 9: Frontend - Handle Tool Messages
- [ ] Add `tool_call` case to WebSocket message handler
- [ ] Invalidate React Query cache on goal changes
- [ ] Set active goal when new goal created

### Step 10: Frontend - UX Polish
- [ ] Show visual feedback when AI is editing goal
- [ ] Toast notifications for goal actions
- [ ] Handle edge case: user editing while AI updates

### Step 11: Testing
- [ ] Test create_goal with various inputs
- [ ] Test update_goal on existing goals
- [ ] Test "current" goal reference
- [ ] Test concurrent user + AI edits
- [ ] Test error handling (invalid goal_id, etc.)

## Updated Files to Modify

| File | Changes |
|------|---------|
| `backend/app/services/claude_service.py` | Add tool definitions, handle tool calls in stream |
| `backend/app/api/routes/chat.py` | Tool execution handler, new WebSocket message types |
| `backend/app/models/goal.py` | Possibly add helper methods for tool operations |
| `frontend/src/hooks/useWebSocket.ts` | Handle `tool_call` message type |
| `frontend/src/lib/websocket.ts` | Add tool_call to message types |
| `frontend/src/types/index.ts` | Add ToolCallMessage type |
| `frontend/src/components/chat/ChatContainer.tsx` | Visual feedback during tool execution |

## System Prompt Additions

Add to Claude's system prompt:

```
## Goal Editing Tools

You have tools to help users create and refine their goals:

- **create_goal**: Use when the user describes a new goal. Create well-structured goals using the appropriate template (SMART, OKR, or custom).
- **update_goal**: Use to refine or expand existing goals. You can add milestones, update deadlines, or improve the goal description.
- **set_goal_phase**: Use to activate draft goals or mark goals as complete when the user indicates they're ready.

Guidelines for using tools:
1. Always explain what you're doing before/after using a tool
2. Ask for confirmation before making major changes to existing goals
3. Use SMART criteria when creating goals unless the user prefers OKR
4. Break down large goals into meaningful milestones
5. Don't overwrite user's work without asking - prefer adding to existing content
```

## Additional Considerations

### Conflict Resolution
- If user is actively typing in editor while AI updates, prefer AI changes but preserve user's unsaved work
- Consider adding a "merge" strategy or showing a diff

### Permission Model
- User can disable AI goal editing in settings (future feature)
- AI should ask before making significant changes

### Undo Support
- Consider tracking AI-made changes for easy undo
- Each tool call could be an undo checkpoint

### Rate Limiting
- Limit tool calls per message to prevent runaway edits
- Add cooldown between rapid tool executions
