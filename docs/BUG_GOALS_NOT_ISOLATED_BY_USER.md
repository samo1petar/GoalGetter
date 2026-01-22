# Bug Report: Goals Not Isolated By User

**Status: FIXED**

## Summary

When a new user is created or a different user logs in, they can see goals from the previous user. Goals should be unique per user but are being leaked across user sessions.

## Severity

**Critical** - This is a data privacy/security issue.

## Steps to Reproduce

1. Login as User A (Ivan)
2. Create a goal
3. Logout
4. Create a new account for User B (Luka) or login as different user
5. Open goals page - **User A's goals are visible to User B**

## Expected Behavior

- Each user should only see their own goals
- New users should see an empty goals list
- Goals should be filtered by `user_id`

## Actual Behavior

- New users see goals from other users
- Goals appear to be shared across all user sessions

## Root Cause Analysis

**Backend is correct** - All goals queries in `backend/app/api/routes/goals.py` properly filter by `current_user["id"]`.

**Frontend is the problem:**

### 1. Query keys not user-scoped

In `frontend/src/hooks/useGoals.ts`:

```typescript
// BAD - no user ID in query key
queryKey: ['goals', params]
queryKey: ['goal', goalId]
queryKey: ['goals', 'statistics']
```

When User B logs in, React Query returns cached data from User A because the cache key is identical.

### 2. Goals cache not cleared on logout

In `frontend/src/hooks/useAuth.ts`, the logout function clears chat cache but not goals:

```typescript
// Current - only clears chat
queryClient.removeQueries({ queryKey: ['chat'] });

// Missing - should also clear goals
queryClient.removeQueries({ queryKey: ['goals'] });
queryClient.removeQueries({ queryKey: ['goal'] });
```

## Files to Modify

| File | Changes Needed |
|------|----------------|
| `frontend/src/hooks/useGoals.ts` | Add user ID to all query keys |
| `frontend/src/hooks/useAuth.ts` | Clear goals cache on logout |

## Suggested Fix

### 1. Update useGoals.ts

```typescript
// Include user ID in query keys
export function useGoals(params?: GoalListParams) {
  const { user } = useAuthStore();
  return useQuery({
    queryKey: ['goals', user?.id, params],
    queryFn: () => goalsApi.list(params),
    enabled: !!user?.id,
  });
}
```

### 2. Update useAuth.ts logout

```typescript
const logout = useCallback(async () => {
  // ... existing code ...

  // Clear ALL user-specific caches
  queryClient.removeQueries({ queryKey: ['chat'] });
  queryClient.removeQueries({ queryKey: ['goals'] });
  queryClient.removeQueries({ queryKey: ['goal'] });

  // ... rest of logout ...
}, [...]);
```

## Priority

**P0** - Fix immediately. This is a privacy violation.

## Labels

`bug`, `security`, `privacy`, `critical`, `goals`

## Related

- Similar to BUG_CHAT_NOT_ISOLATED_BY_USER.md (same root cause pattern)

---

## Resolution

**Fixed on 2026-01-21**

### Changes Made

| File | Change |
|------|--------|
| `frontend/src/hooks/useGoals.ts` | Added `user?.id` to all query keys (`['goals', user?.id, params]`, `['goal', user?.id, goalId]`, `['goals', 'statistics', user?.id]`) and added `enabled: !!user?.id` checks |
| `frontend/src/hooks/useAuth.ts` | Added `queryClient.removeQueries({ queryKey: ['goals'] })` and `queryClient.removeQueries({ queryKey: ['goal'] })` on logout |

### Verification Steps

1. Login as User A, create a goal
2. Logout
3. Create new User B or login as different user
4. Verify goals list is empty (or shows only User B's goals)
