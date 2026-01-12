# Sprint 2: Goal Management - COMPLETE

**Completed**: 2026-01-12

## Summary

Sprint 2 implemented the complete Goal Management system for GoalGetter, including full CRUD operations, goal templates (SMART, OKR, Custom), phase management, and PDF export functionality.

## Files Created

### Models
- `backend/app/models/goal.py` - Goal and GoalTemplate models for MongoDB

### Schemas
- `backend/app/schemas/goal.py` - Pydantic schemas for request/response validation

### Services
- `backend/app/services/goal_service.py` - Goal business logic (CRUD, filtering, statistics)
- `backend/app/services/pdf_service.py` - PDF generation using ReportLab

### API Routes
- `backend/app/api/routes/goals.py` - Goal CRUD endpoints
- `backend/app/api/routes/templates.py` - Goal template endpoints

### Modified Files
- `backend/app/main.py` - Registered goals and templates routers

## API Endpoints Implemented

### Goals (`/api/v1/goals`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/goals` | Create a new goal |
| GET | `/goals` | List user's goals (paginated, filterable) |
| GET | `/goals/statistics` | Get goal statistics by phase |
| POST | `/goals/from-template` | Create goal from template |
| GET | `/goals/{id}` | Get specific goal |
| PUT | `/goals/{id}` | Update goal |
| PATCH | `/goals/{id}/phase` | Update goal phase |
| DELETE | `/goals/{id}` | Delete goal |
| GET | `/goals/{id}/export` | Export goal as PDF |

### Templates (`/api/v1/templates`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/templates` | List all templates |
| GET | `/templates/{type}` | Get specific template |
| GET | `/templates/{type}/preview` | Get template preview with example |

## Features Implemented

### 1. Goal Model
- User-specific goals with MongoDB ObjectId references
- Phase tracking: `draft`, `active`, `completed`, `archived`
- Template types: `smart`, `okr`, `custom`
- Metadata support: deadline, milestones, tags

### 2. Goal CRUD Operations
- Create goals with full validation
- List goals with pagination and filtering
- Filter by phase, template type, tags
- Full-text search in title and content
- Sorting by created_at, updated_at, title
- Update and delete with ownership verification

### 3. Goal Templates
- **SMART**: Specific, Measurable, Achievable, Relevant, Time-bound
- **OKR**: Objectives and Key Results
- **Custom**: Free-form goal template
- Template preview with usage examples
- Create goals pre-filled with template content

### 4. Phase Management
- Update goal phase via dedicated endpoint
- Goal statistics aggregation by phase
- Automatic timestamp updates

### 5. PDF Export
- Professional PDF generation with ReportLab
- Brand colors and custom styling
- Markdown-to-PDF conversion for content
- Includes title, metadata, milestones, and tags
- Downloadable attachment with safe filename

## Testing Results

All endpoints tested successfully:

```bash
# Templates
GET /api/v1/templates - 200 OK (returns 3 templates)
GET /api/v1/templates/smart - 200 OK
GET /api/v1/templates/smart/preview - 200 OK

# Goals CRUD
POST /api/v1/goals - 201 Created
GET /api/v1/goals - 200 OK (paginated)
GET /api/v1/goals/{id} - 200 OK
PUT /api/v1/goals/{id} - 200 OK
PATCH /api/v1/goals/{id}/phase - 200 OK
DELETE /api/v1/goals/{id} - 204 No Content

# Special Operations
GET /api/v1/goals/statistics - 200 OK
POST /api/v1/goals/from-template - 201 Created
GET /api/v1/goals/{id}/export - 200 OK (PDF file)
```

## Security

- All endpoints protected with `get_current_active_user` dependency
- Users can only access their own goals (user_id filtering)
- Input validation via Pydantic schemas
- ObjectId validation for MongoDB queries

## How to Test

1. Start the services:
```bash
docker compose up -d mongodb redis
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

2. Access Swagger UI: http://localhost:8000/api/v1/docs

3. Create an account and authenticate:
```bash
# Sign up
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","name":"Test User","password":"testpass123"}'

# Use the returned access_token for subsequent requests
```

4. Test goal endpoints:
```bash
# Create a goal
curl -X POST http://localhost:8000/api/v1/goals \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"title":"My Goal","content":"Goal content","template_type":"custom"}'

# List goals
curl -X GET http://localhost:8000/api/v1/goals \
  -H "Authorization: Bearer <token>"

# Export as PDF
curl -X GET http://localhost:8000/api/v1/goals/{id}/export \
  -H "Authorization: Bearer <token>" \
  -o goal.pdf
```

## Notes for Next Sprint

Sprint 3 (Real-time Chat & AI Coach) will build upon this foundation:
- Goals will be passed to the AI coach as context
- Chat messages may reference specific goals
- Goal updates can be suggested by the coach

## Dependencies Used

- `reportlab==4.0.9` - PDF generation
- Existing: `motor`, `pydantic`, `fastapi`

---

**Sprint 2 Status: COMPLETE**
