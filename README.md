# GoalGetter

**AI-Powered Goal Achievement Platform with Tony Robbins Coaching**

GoalGetter helps users set and achieve meaningful goals through an AI coach that embodies the Tony Robbins persona - energizing, goal-oriented, compassionate, and direct.

## Overview

GoalGetter features two distinct phases:

### Phase 1: Goal Setting
- Unlimited access to AI coach
- Collaborative goal creation in split-screen interface
- Real-time feedback and suggestions
- Goal templates (SMART, OKR frameworks)
- Coach ensures goals are achievable and realistic

### Phase 2: Goal Tracking
- Scheduled check-ins with the coach
- Fixed-interval meetings (weekly, bi-weekly, or monthly)
- Gated chat access (only during meetings)
- Calendar integration with Google Calendar
- Email reminders and meeting invites

## Key Features

- **Split-Screen Interface:** Document editor (left) + Real-time chat with AI coach (right)
- **OAuth Authentication:** Sign up with Google or GitHub
- **Real-time Chat:** WebSocket-powered conversation with Claude AI
- **Meeting Scheduling:** Automated scheduling with calendar sync
- **Email Notifications:** Reminders for upcoming meetings
- **Goal Templates:** Pre-built frameworks (SMART, OKR)
- **PDF Export:** Export goals as formatted PDF documents
- **Progress Tracking:** Monitor goal achievement over time

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **MongoDB** - NoSQL database for flexible goal storage
- **Redis** - Caching and message broker
- **Anthropic Claude** - AI coach with Tony Robbins persona
- **Celery** - Background task processing
- **Python-SocketIO** - Real-time WebSocket communication

### Infrastructure
- **Docker** - Containerization
- **MongoDB Atlas** - Managed database (production)
- **Redis Cloud** - Managed cache (production)

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- Anthropic API key
- Google OAuth credentials (optional)
- SendGrid API key (optional, for emails)

### Setup

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd GoalGetter
   ```

2. **Setup environment variables:**
   ```bash
   cp backend/.env.example backend/.env
   # Edit backend/.env and add your API keys
   ```

3. **Start services with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

4. **Access the application:**
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/api/v1/docs
   - Flower (Celery monitoring): http://localhost:5555

### Local Development

For detailed backend setup, see [backend/README.md](backend/README.md)

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Project Structure

```
GoalGetter/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/routes/  # API endpoints
│   │   ├── core/        # Configuration
│   │   ├── models/      # Database models
│   │   ├── schemas/     # Pydantic schemas
│   │   ├── services/    # Business logic
│   │   └── main.py      # FastAPI app
│   └── requirements.txt
├── frontend/            # Frontend application (TBD)
├── docker-compose.yml   # Docker services
├── PROJECT_PLAN.md      # Comprehensive project documentation
└── README.md           # This file
```

## Documentation

- **[PROJECT_PLAN.md](PROJECT_PLAN.md)** - Comprehensive project plan with:
  - Detailed tech stack decisions
  - Complete implementation roadmap (6 sprints)
  - Database schema
  - API endpoint reference
  - Deployment guide
  - Cost estimates
  - Future enhancements

- **[backend/README.md](backend/README.md)** - Backend-specific documentation

## API Documentation

Once the server is running, visit:
- **Swagger UI:** http://localhost:8000/api/v1/docs
- **ReDoc:** http://localhost:8000/api/v1/redoc

## Development Roadmap

See [PROJECT_PLAN.md](PROJECT_PLAN.md) for the complete 6-sprint roadmap.

### Sprint 1: Foundation & Authentication ✅
- FastAPI project setup
- MongoDB and Redis connections
- OAuth authentication

### Sprint 2: Goal Management
- CRUD operations for goals
- Goal templates system
- PDF export functionality

### Sprint 3: Real-time Chat & AI Coach
- WebSocket integration
- Anthropic Claude API
- Tony Robbins persona

### Sprint 4: Meeting Scheduling & Calendar
- Meeting scheduling logic
- Google Calendar integration
- Meeting access gates

### Sprint 5: Notifications & Background Jobs
- Email notifications
- Celery tasks for reminders
- Scheduled meeting updates

### Sprint 6: Polish & Deployment
- Error handling and logging
- Docker deployment
- Production deployment

## Environment Variables

Key environment variables (see `backend/.env.example` for full list):

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-your-api-key
MONGODB_URI=mongodb://localhost:27017/goalgetter
REDIS_URL=redis://localhost:6379/0

# Optional but recommended
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
SENDGRID_API_KEY=your-sendgrid-api-key
```

## Testing

```bash
cd backend
pytest
pytest --cov=app tests/
```

## Deployment

### Option 1: Railway (Recommended)
1. Push code to GitHub
2. Connect Railway to your repository
3. Add MongoDB and Redis plugins
4. Configure environment variables
5. Deploy!

### Option 2: Docker
```bash
docker-compose -f docker-compose.yml up -d
```

See [PROJECT_PLAN.md](PROJECT_PLAN.md) for detailed deployment instructions.

## Contributing

This is a proprietary project. Please contact the maintainers for contribution guidelines.

## License

Proprietary - All rights reserved

## Support

For questions or issues:
- Create an issue in the repository
- Contact: support@goalgetter.com

## Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- AI powered by [Anthropic Claude](https://www.anthropic.com/)
- Inspired by Tony Robbins' coaching methodology

---

**GoalGetter** - Transform your goals into achievements with AI-powered coaching.
