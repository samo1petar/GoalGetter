# Feature: Auto-Switch Goal Layout When AI Coach Uses Tools

## Overview
When the AI Coach uses any tool (create_goal, update_goal, set_goal_phase), automatically switch the goal layout to display that goal at the right moment. This allows users to see the goal being modified in real-time.

## Requirements

### For `update_goal` and `set_goal_phase`:
- UI switches to the goal BEFORE the tool executes
- User sees the update happen in real-time

### For `create_goal`:
1. Create a minimal goal (title only, empty content)
2. Switch focus to the new goal
3. Populate the goal with full content (milestones, description, etc.)
- User sees the goal appear, then watches it get populated

---

## Implementation Tasks

### Task 1: Add `_create_goal_minimal` method to GoalToolHandler

**File:** `backend/app/services/goal_tool_handler.py`

Add a new method after the existing `_create_goal` method:

```python
async def _create_goal_minimal(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Create a minimal goal with just title - returns goal_id for focus."""
    try:
        title = tool_input.get("title", "New Goal")
        template_type = tool_input.get("template_type", "custom")

        goal_doc = GoalModel.create_goal_document(
            user_id=self.user_id,
            title=title,
            content="",  # Empty content - will be populated
            template_type=template_type,
            metadata={
                "content_format": "markdown",
                "milestones": [],
                "tags": [],
            }
        )

        result = await self.db.goals.insert_one(goal_doc)
        goal_id = str(result.inserted_id)

        return {"success": True, "goal_id": goal_id}
    except Exception as e:
        logger.error(f"Error creating minimal goal: {e}")
        return {"success": False, "error": str(e)}
```

---

### Task 2: Update chat.py Tool Execution Logic

**File:** `backend/app/api/routes/chat.py`

Find the tool execution block (around line 606-626 where `tool_call` chunk is handled). Replace the tool execution logic with:

```python
elif chunk["type"] == "tool_call":
    # Collect tool call info
    tool_name = chunk.get("tool_name")
    tool_id = chunk.get("tool_id")
    tool_input = chunk.get("tool_input", {})

    logger.info(f"Executing tool: {tool_name} with input: {tool_input}")

    # Handle focus_goal for update_goal and set_goal_phase BEFORE execution
    if tool_name in ["update_goal", "set_goal_phase"]:
        goal_id_to_focus = tool_input.get("goal_id")
        # Resolve "current" to actual goal ID
        if goal_id_to_focus == "current":
            goal_id_to_focus = active_goal_id

        if goal_id_to_focus:
            await websocket.send_json({
                "type": "focus_goal",
                "goal_id": goal_id_to_focus,
            })

    # Handle create_goal with two-step process
    if tool_name == "create_goal":
        # Step 1: Create minimal goal
        minimal_result = await tool_handler._create_goal_minimal(tool_input)

        if minimal_result.get("success"):
            goal_id = minimal_result["goal_id"]

            # Step 2: Send focus_goal to switch to the new goal
            await websocket.send_json({
                "type": "focus_goal",
                "goal_id": goal_id,
            })

            # Invalidate goals cache so frontend fetches the new goal
            # (handled by frontend on focus_goal)

            # Step 3: Populate the goal with full content
            populate_input = {
                "goal_id": goal_id,
                "title": tool_input.get("title"),
                "content": tool_input.get("content"),
                "deadline": tool_input.get("deadline"),
                "milestones": tool_input.get("milestones"),
                "tags": tool_input.get("tags"),
            }
            tool_result = await tool_handler._update_goal(populate_input, goal_id)
            tool_result["goal_id"] = goal_id  # Ensure goal_id is in result
        else:
            tool_result = minimal_result
    else:
        # Regular tool execution for update_goal and set_goal_phase
        tool_result = await tool_handler.execute_tool(
            tool_name=tool_name,
            tool_input=tool_input,
            active_goal_id=active_goal_id,
        )

    # Send tool result to frontend (rest of existing code continues...)
    await websocket.send_json({
        "type": "tool_call",
        "tool": tool_name,
        "tool_result": tool_result,
    })
```

---

### Task 3: Update TypeScript Types

**File:** `frontend/src/types/index.ts`

Update the `WebSocketMessage` interface:

1. Add `'focus_goal'` to the type union:
```typescript
type: 'connected' | 'typing' | 'response_chunk' | 'response' | 'error' | 'pong' | 'tool_call' | 'welcome' | 'focus_goal';
```

2. Add `goal_id` field after `tool_result`:
```typescript
// Focus goal field (for switching to goal before tool execution)
goal_id?: string;
```

---

### Task 4: Handle focus_goal in useWebSocket

**File:** `frontend/src/hooks/useWebSocket.ts`

Add a new case in the message handler switch statement, BEFORE the `case 'tool_call':` block:

```typescript
case 'focus_goal':
    // AI Coach is about to modify this goal - switch to it
    if (data.goal_id) {
        setActiveGoalId(data.goal_id);
        // Invalidate goals query to fetch newly created goals
        queryClient.invalidateQueries({ queryKey: ['goals'] });
    }
    break;
```

---

## Files to Modify Summary

| File | Change |
|------|--------|
| `backend/app/services/goal_tool_handler.py` | Add `_create_goal_minimal` method |
| `backend/app/api/routes/chat.py` | Add focus_goal logic, special create_goal handling |
| `frontend/src/types/index.ts` | Add `focus_goal` to WebSocketMessage type, add `goal_id` field |
| `frontend/src/hooks/useWebSocket.ts` | Handle `focus_goal` message type |

---

## Testing Instructions

### Test create_goal:
1. Ask AI Coach: "Create a goal to learn Spanish in 6 months"
2. **Expected:**
   - Empty goal appears in editor with title
   - Goal gets populated with content, milestones, etc.
   - User watches the goal being built

### Test update_goal:
1. Create two goals manually (Goal A and Goal B)
2. View Goal A in the editor
3. Ask AI Coach: "Update the title of Goal B to 'Test Title'"
4. **Expected:** UI switches to Goal B BEFORE the update, then Goal B is updated

### Test set_goal_phase:
1. While viewing Goal A, ask: "Mark Goal B as active"
2. **Expected:** UI switches to Goal B BEFORE the phase change
