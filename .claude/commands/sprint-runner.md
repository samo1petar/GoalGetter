# Sprint Runner

Implement the next pending sprint for the GoalGetter project.

## Instructions

1. Read `.claude/sprint-tracker.json` to identify the current pending sprint
2. Read `.claude/agents/sprint-runner.md` for detailed implementation instructions
3. Implement ALL tasks for that sprint completely
4. Test the implementation by running the app
5. Update the sprint tracker to mark the sprint as completed
6. Create a completion report at `backend/SPRINT{N}_COMPLETE.md`

## Quick Reference

**Sprint 2**: Goal Management - CRUD, templates, PDF export
**Sprint 3**: Real-time Chat - WebSocket, Claude AI, Tony Robbins persona
**Sprint 4**: Meeting Scheduling - Meetings, calendar integration
**Sprint 5**: Notifications - Celery, SendGrid, background jobs
**Sprint 6**: Polish - Error handling, testing, deployment

## Important

- Complete ONE sprint only, then exit
- Follow patterns from existing code (auth implementation)
- Test endpoints before marking complete
- Handle missing config (API keys) gracefully

## Start

Begin by reading the sprint tracker:
```
cat .claude/sprint-tracker.json
```

Then follow the detailed instructions in `.claude/agents/sprint-runner.md`
