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
- **OAuth Authentication:** Sign up with Google or email/password
- **Two-Factor Authentication:** TOTP-based 2FA with backup codes
- **Password Reset:** Secure email-based password recovery
- **Real-time Chat:** WebSocket-powered conversation with Claude AI
- **Meeting Scheduling:** Automated scheduling with calendar sync
- **Email Notifications:** Reminders for upcoming meetings
- **Goal Templates:** Pre-built frameworks (SMART, OKR)
- **PDF Export:** Export goals as formatted PDF documents
- **Progress Tracking:** Monitor goal achievement over time
- **Rate Limiting:** Fair usage enforcement with Redis-backed rate limiting
- **Structured Logging:** JSON logging for production environments
- **Comprehensive Error Handling:** Custom exceptions with consistent API responses

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **MongoDB** - NoSQL database for flexible goal storage
- **Redis** - Caching, rate limiting, and message broker
- **Anthropic Claude** - AI coach with Tony Robbins persona
- **Celery** - Background task processing
- **WebSocket** - Real-time communication
- **PyOTP** - Two-factor authentication

### Frontend
- **Next.js 14** - React framework with App Router
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first styling
- **Zustand** - State management
- **Radix UI** - Accessible component primitives
- **BlockNote** - Rich text editor

### Infrastructure
- **Docker** - Containerization
- **MongoDB Atlas** - Managed database (production)
- **Redis Cloud** - Managed cache (production)
- **Railway** - Recommended deployment platform

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.12+ (for local development)
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
   # Development
   docker-compose up -d

   # Production
   docker-compose -f docker-compose.prod.yml up -d
   ```

4. **Access the application:**
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/api/v1/docs
   - ReDoc: http://localhost:8000/api/v1/redoc
   - Flower (Celery monitoring): http://localhost:5555

### Local Development

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Project Structure

```
GoalGetter/
├── backend/
│   ├── app/
│   │   ├── api/routes/      # API endpoints
│   │   ├── core/            # Configuration, database, security
│   │   ├── models/          # MongoDB document models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Business logic
│   │   ├── tasks/           # Celery background tasks
│   │   ├── templates/       # Email templates
│   │   └── main.py          # FastAPI app
│   ├── tests/               # Pytest tests
│   ├── Dockerfile           # Multi-stage Docker build
│   ├── railway.toml         # Railway deployment config
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/             # Next.js pages
│   │   ├── components/      # React components
│   │   ├── hooks/           # Custom React hooks
│   │   ├── lib/             # API clients, utilities
│   │   ├── stores/          # Zustand state stores
│   │   └── types/           # TypeScript types
│   ├── Dockerfile           # Multi-stage Docker build
│   └── railway.toml         # Railway deployment config
├── docker-compose.yml       # Development Docker setup
├── docker-compose.prod.yml  # Production Docker setup
├── DEPLOYMENT.md            # Deployment guide
├── PROJECT_PLAN.md          # Project documentation
└── README.md                # This file
```

## API Documentation

Once the server is running, visit:
- **Swagger UI:** http://localhost:8000/api/v1/docs
- **ReDoc:** http://localhost:8000/api/v1/redoc

### API Endpoints

#### Authentication
- `POST /api/v1/auth/signup` - Register new user
- `POST /api/v1/auth/login` - Login with email/password (supports 2FA)
- `POST /api/v1/auth/logout` - Logout (blacklists token)
- `POST /api/v1/auth/refresh` - Refresh access token
- `GET /api/v1/auth/google` - Google OAuth
- `GET /api/v1/auth/me` - Get current user
- `POST /api/v1/auth/forgot-password` - Request password reset
- `POST /api/v1/auth/reset-password` - Reset password with token
- `POST /api/v1/auth/2fa/setup` - Setup two-factor authentication
- `POST /api/v1/auth/2fa/verify` - Verify and enable 2FA
- `POST /api/v1/auth/2fa/disable` - Disable 2FA

#### Goals
- `GET /api/v1/goals` - List goals (with pagination, filtering)
- `POST /api/v1/goals` - Create goal
- `GET /api/v1/goals/{id}` - Get goal
- `PUT /api/v1/goals/{id}` - Update goal
- `DELETE /api/v1/goals/{id}` - Delete goal
- `GET /api/v1/goals/{id}/export` - Export as PDF
- `POST /api/v1/goals/from-template` - Create from template

#### Templates
- `GET /api/v1/templates` - List templates
- `GET /api/v1/templates/{type}` - Get template (smart, okr, custom)

#### Chat
- `WS /api/v1/chat/ws` - WebSocket chat
- `GET /api/v1/chat/access` - Check chat access
- `GET /api/v1/chat/history` - Get chat history
- `POST /api/v1/chat/send` - Send message (HTTP)
- `DELETE /api/v1/chat/history` - Clear history

#### Meetings
- `POST /api/v1/meetings/setup` - Setup recurring meetings
- `POST /api/v1/meetings` - Create meeting
- `GET /api/v1/meetings` - List meetings
- `GET /api/v1/meetings/next` - Get next meeting
- `GET /api/v1/meetings/{id}` - Get meeting
- `PUT /api/v1/meetings/{id}` - Update meeting
- `DELETE /api/v1/meetings/{id}` - Cancel meeting
- `POST /api/v1/meetings/{id}/complete` - Complete meeting

#### Users
- `GET /api/v1/users/me` - Get profile
- `PUT /api/v1/users/me` - Update profile
- `PATCH /api/v1/users/me/phase` - Change phase

## Development

### Running Tests

```bash
cd backend
pytest                          # Run all tests
pytest --cov=app tests/         # With coverage
pytest -v tests/test_auth.py    # Specific test file
```

### Code Formatting

```bash
black app/
isort app/
flake8 app/
```

### Type Checking

```bash
mypy app/
```

## Development Roadmap

All 6 sprints have been completed.

### Sprint 1: Foundation & Authentication
- FastAPI project setup
- MongoDB and Redis connections
- JWT authentication
- OAuth with Google

### Sprint 2: Goal Management
- Goal CRUD operations
- Goal templates (SMART, OKR)
- PDF export functionality

### Sprint 3: Real-time Chat & AI Coach
- WebSocket integration
- Anthropic Claude API
- Tony Robbins persona
- Chat access control

### Sprint 4: Meeting Scheduling & Calendar
- Meeting scheduling
- Google Calendar integration
- Phase transitions

### Sprint 5: Notifications & Background Jobs
- Celery configuration
- Email notifications (SendGrid)
- Scheduled tasks (meeting reminders)
- Rate limiting (slowapi)

### Sprint 6: Polish & Deployment
- Custom exception classes
- Structured JSON logging
- Security middleware (headers, CORS)
- Production Docker setup
- Comprehensive pytest tests
- Deployment documentation

## Environment Variables

Key environment variables (see `backend/.env.example` for full list):

```bash
# Required
SECRET_KEY=<32-char-secret>
JWT_SECRET_KEY=<32-char-secret>
MONGODB_URI=mongodb://localhost:27017/goalgetter
REDIS_URL=redis://localhost:6379/0

# AI Coach (required for chat)
ANTHROPIC_API_KEY=sk-ant-your-api-key

# Optional
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
SENDGRID_API_KEY=your-sendgrid-api-key
SENTRY_DSN=your-sentry-dsn
```

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

### Quick Deploy

```bash
# Production with Docker
docker-compose -f docker-compose.prod.yml up -d
```

### Cloud Options
- **Railway** - Simple deployment with built-in MongoDB/Redis
- **AWS ECS** - Container deployment with ECR
- **Google Cloud Run** - Serverless containers
- **DigitalOcean App Platform** - Easy setup

## Security Features

- JWT authentication with refresh tokens
- Token blacklisting for secure logout
- Two-factor authentication (TOTP) with backup codes
- Password hashing with bcrypt
- Secure password reset via email
- OAuth state validation (CSRF protection)
- Rate limiting on all endpoints
- CORS configuration
- Security headers (X-Frame-Options, X-Content-Type-Options, etc.)
- Input validation with Pydantic
- Request ID tracking

## Monitoring

- Health check endpoint: `/health`
- Status endpoint: `/status`
- Structured JSON logging
- Sentry integration (optional)
- Celery Flower for task monitoring

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
