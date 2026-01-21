# Bug Report & Feature Request: Goal Sync and Trace Logging

## Bug: Permission Denied When Writing Trace Logs

### Summary

Intermittent permission denied errors when the OpenAI service attempts to write trace logs during goal editing operations.

### Error Message

```json
{
  "timestamp": "2026-01-21T11:06:15.859727Z",
  "level": "WARNING",
  "name": "app.services.llm.openai_service",
  "message": "Failed to write trace log: [Errno 13] Permission denied: 'logs/openai_traces.jsonl'",
  "module": "openai_service",
  "function": "_write_trace",
  "line": 326
}
```

### Reproduction Steps

1. Open the application
2. Use AI Coach to create or edit a goal
3. Error appears intermittently in logs

### Possible Causes

- File permissions on `logs/openai_traces.jsonl` are incorrect
- Multiple processes/threads attempting to write simultaneously (race condition)
- Log file owned by different user (e.g., root vs app user in Docker)
- Log directory doesn't exist or has wrong permissions
- File handle not being released properly after writes

### Investigation Needed

- [ ] Check how AI Coach goal creation function tags goals
- [ ] Check how goal IDs are assigned during AI-assisted creation
- [ ] Verify file permissions on `logs/` directory and `openai_traces.jsonl`
- [ ] Check if running in Docker with volume mount permission issues
- [ ] Review `_write_trace` function at `openai_service.py:326`

### Suggested Fix

1. Ensure `logs/` directory is created with proper permissions on startup
2. Use file locking mechanism for concurrent writes
3. Handle permission errors gracefully (don't just warn, attempt recovery)
4. Consider using a proper logging handler instead of direct file writes

---

## Feature Request: Real-Time Goal Context for AI Coach

### Summary

AI Coach should have immediate access to the latest goal data, including changes made seconds ago. Currently, there appears to be stale data when the Coach generates or updates goals.

### Problem

When a user:
1. Creates or updates a goal
2. Immediately asks AI Coach for help with that goal

The AI Coach may not see the most recent changes. There's a sync delay causing the Coach to work with outdated goal information.

### Current Behavior

- AI Coach retrieves goal data that may be stale
- Updates made 2+ seconds ago may not be visible to the Coach
- Goal text created by AI Coach may not be immediately available for subsequent operations

### Expected Behavior

- AI Coach should always see the latest goal state
- Any goal creation, update, or deletion should be immediately reflected
- Real-time consistency between user actions and AI Coach context

### Technical Investigation Needed

- [ ] How does AI Coach fetch goal context before generating responses?
- [ ] Is there caching involved in goal retrieval?
- [ ] Are database writes committed before AI Coach queries?
- [ ] Is there an async operation that hasn't completed?
- [ ] How are goals tagged when created via AI Coach vs manual creation?
- [ ] How are goal IDs assigned during AI-assisted creation?

### Possible Causes

1. **Caching**: Goal data cached and not invalidated on updates
2. **Async writes**: Database write not awaited before Coach query
3. **Stale context**: Coach context built before the latest changes are persisted
4. **Transaction isolation**: Read happening before write transaction commits
5. **Message history**: Coach using outdated message history that doesn't reflect DB state

### Proposed Solution

1. **Invalidate cache** on any goal mutation (create/update/delete)
2. **Refresh goal context** immediately before AI Coach generates a response
3. **Ensure await** on all database operations before proceeding
4. **Pass fresh data** directly to Coach instead of re-querying
5. **Add timestamp** to goal context to verify freshness during debugging

### Acceptance Criteria

- [ ] AI Coach sees goal changes immediately after they're made
- [ ] No stale data issues when editing goals in quick succession
- [ ] Goal creation via AI Coach is immediately visible for follow-up operations
- [ ] Trace logging works without permission errors

## Priority

High - Affects core AI Coach functionality

## Labels

`bug`, `feature`, `ai-coach`, `data-sync`, `logging`
