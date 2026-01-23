# Feature Request: Disable Goal Editing Tools for OpenAI Models

**Status: IMPLEMENTED**

## Overview

Remove the ability for OpenAI models to use goal creation and editing tools (`create_goal`, `update_goal`, `set_goal_phase`). The tools and their handler functions should remain intact - only the access from OpenAI models should be disabled.

## Rationale

- OpenAI model integration is secondary to Claude
- Goal editing via AI is a premium feature best served by Claude
- Reduces complexity and potential issues with OpenAI tool calling
- OpenAI can still provide coaching advice, just cannot directly modify goals

## Current State

### OpenAI Service (`backend/app/services/llm/openai_service.py`)

1. **OPENAI_TOOLS constant** (lines 107-245): Defines three goal tools:
   - `create_goal`
   - `update_goal`
   - `set_goal_phase`

2. **System prompt** (lines 27-103): Contains instructions about using goal editing tools:
   - Lines 75-91 describe the tools and how to use them

3. **get_tools() method** (lines 537-539): Returns `OPENAI_TOOLS`

4. **stream_message() method** (lines 748-751): Passes tools to API when `use_tools=True`:
   ```python
   if use_tools:
       api_params["tools"] = OPENAI_TOOLS
       api_params["tool_choice"] = "auto"
   ```

### Claude Service (No Changes Needed)

Claude service in `backend/app/services/llm/claude_service.py` should continue to have full tool access including `schedule_meeting`.

## Requirements

### 1. Remove Tool Definitions from OpenAI Service

**Do NOT delete** the `OPENAI_TOOLS` constant - just don't use it.

Modify `get_tools()` method to return an empty list:

```python
def get_tools(self) -> List[Dict[str, Any]]:
    """Return tool definitions in OpenAI's format.

    Note: Goal editing tools are disabled for OpenAI models.
    Only Claude has access to create_goal, update_goal, and set_goal_phase.
    """
    return []
```

### 2. Update stream_message() to Not Pass Tools

In the `stream_message()` method, modify the tool handling section:

```python
# Before (lines 748-751):
if use_tools:
    api_params["tools"] = OPENAI_TOOLS
    api_params["tool_choice"] = "auto"

# After:
# Goal editing tools are disabled for OpenAI models.
# The use_tools parameter is accepted but ignored.
# Only Claude has access to goal manipulation tools.
```

Simply remove or comment out the lines that add tools to api_params.

### 3. Update System Prompt for OpenAI

Create a separate system prompt for OpenAI that does NOT include the goal editing tool instructions.

Replace the `TONY_ROBBINS_SYSTEM_PROMPT` used in OpenAI service with a version that:
- Removes lines 75-91 (GOAL EDITING TOOLS section and guidelines)
- Adds a note that the AI cannot directly edit goals but can provide guidance

**New section to add instead:**

```
IMPORTANT LIMITATION:
You cannot directly create or modify goals in this mode. Instead:
- Provide clear, actionable suggestions for goals the user should create
- Help them refine their thinking about goals
- Encourage them to use the goal editor to capture their goals
- You can still see their existing goals and drafts for context
```

### 4. Update Trace Logging

In `log_request()` method, the `has_tools` will now always be False for OpenAI, which is correct.

## Implementation Checklist

- [x] Modify `get_tools()` to return empty list
- [x] Remove/comment out tool passing in `stream_message()`
- [x] Create OpenAI-specific system prompt without tool instructions
- [x] Add limitation note to OpenAI system prompt
- [ ] Test that OpenAI responses work without tools
- [ ] Verify Claude still has full tool access

## Files to Modify

| File | Changes |
|------|---------|
| `backend/app/services/llm/openai_service.py` | Disable tool access, update system prompt |

## Notes

- Keep `OPENAI_TOOLS` constant in the file (commented or as reference) in case tools need to be re-enabled later
- The `use_tools` parameter in `stream_message()` can remain in the signature for API compatibility but will be ignored
- No changes needed to `goal_tool_handler.py` or any frontend code
- No changes needed to Claude service

## Priority

**P2** - Feature refinement to differentiate provider capabilities

---

## Resolution

**Implemented on 2026-01-23**

### Changes Made to `backend/app/services/llm/openai_service.py`

1. **System prompt updated** (lines 75-80):
   - Replaced "GOAL EDITING TOOLS" section with "IMPORTANT LIMITATION" section
   - New text explains that OpenAI cannot create/modify goals directly
   - Instructs AI to provide guidance and encourage using the goal editor

2. **`get_tools()` method updated** (lines 527-533):
   - Now returns an empty list
   - Added docstring explaining tools are disabled for OpenAI

3. **`stream_message()` method updated** (lines 742-747):
   - Commented out the code that passes tools to the API
   - Added explanatory comments about why tools are disabled
   - `use_tools` parameter kept in signature for API compatibility

4. **`OPENAI_TOOLS` constant preserved** (lines 97-235):
   - Kept in file for reference/future use
   - Just not used in API calls
