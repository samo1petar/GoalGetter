# Bug Report: Create Goal Fails After Focus Goal Feature

## Summary
After implementing the "Focus Goal on Tool Use" feature, the `create_goal` tool fails with "Failed to create goal" error. Goals are not being created.

## Related Feature
- Feature file: `docs/FEATURE_FOCUS_GOAL_ON_TOOL_USE.md`
- Implementation changed the `create_goal` flow to a two-step process

## Error Message
```
Failed to create goal
```

## Expected Behavior
When user asks AI Coach to create a goal:
1. Minimal goal should be created (title only)
2. UI should switch to the new goal
3. Goal should be populated with full content

## Actual Behavior
Goal creation fails entirely. No goal is created.

## Files Modified by Feature
- `backend/app/api/routes/chat.py` - Added two-step create_goal logic (lines 627-656)
- `backend/app/services/goal_tool_handler.py` - Added `_create_goal_minimal` method (lines 137-161)

## Suspected Areas to Investigate
1. `_create_goal_minimal` method in `goal_tool_handler.py`
2. Two-step process in `chat.py` (create minimal → focus → populate)
3. The `_update_goal` call that populates the goal after creation

## Steps to Reproduce
1. Start the application
2. Open the chat with AI Coach
3. Ask: "Create a goal to learn Spanish"
4. Observe error: "Failed to create goal"

## Logs
Check backend logs for errors during tool execution. Look for:
- "Error creating minimal goal"
- Errors in `_update_goal` after minimal creation
- Any exception traces
