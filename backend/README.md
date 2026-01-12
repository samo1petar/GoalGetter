# GoalGetter Backend

FastAPI backend for the GoalGetter AI-powered goal achievement platform.

## Quick Start

### Prerequisites

- Python 3.11+
- MongoDB
- Redis
- Anthropic API key

### Local Development Setup

1. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Setup environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys and configuration
   ```

4. **Run with Docker Compose (recommended):**
   ```bash
   cd ..
   docker-compose up -d mongodb redis
   cd backend
   uvicorn app.main:app --reload
   ```

5. **Or run everything with Docker:**
   ```bash
   cd ..
   docker-compose up
   ```

### Access the API

- **API Docs:** http://localhost:8000/api/v1/docs
- **ReDoc:** http://localhost:8000/api/v1/redoc
- **Health Check:** http://localhost:8000/health
- **Flower (Celery monitoring):** http://localhost:5555

## Project Structure

```
backend/
├── app/
│   ├── api/routes/       # API endpoints
│   ├── core/             # Core configuration
│   ├── models/           # Database models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic
│   ├── tasks/            # Celery tasks
│   ├── utils/            # Utilities
│   └── main.py           # FastAPI app
├── tests/                # Test files
├── requirements.txt
├── Dockerfile
└── .env.example
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/signup` - Register
- `POST /api/v1/auth/login` - Login
- `GET /api/v1/auth/google` - OAuth with Google

### Goals
- `GET /api/v1/goals` - List goals
- `POST /api/v1/goals` - Create goal
- `PUT /api/v1/goals/{id}` - Update goal
- `DELETE /api/v1/goals/{id}` - Delete goal

### Chat
- `WS /api/v1/ws/chat` - WebSocket chat
- `GET /api/v1/chat/history` - Chat history

### Meetings
- `POST /api/v1/meetings/setup` - Setup meetings
- `GET /api/v1/meetings` - List meetings
- `PUT /api/v1/meetings/{id}` - Update meeting

## Development

### Running Tests
```bash
pytest
pytest --cov=app tests/
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

## Environment Variables

See `.env.example` for all required configuration options.

Key variables:
- `ANTHROPIC_API_KEY` - Anthropic Claude API key (required)
- `MONGODB_URI` - MongoDB connection string
- `REDIS_URL` - Redis connection URL
- `GOOGLE_CLIENT_ID` - Google OAuth client ID
- `SENDGRID_API_KEY` - SendGrid API key for emails

## Deployment

See the main [PROJECT_PLAN.md](../PROJECT_PLAN.md) for detailed deployment instructions.

Quick deploy with Railway:
1. Push to GitHub
2. Connect Railway to your repo
3. Add environment variables
4. Deploy!

## License

Proprietary - All rights reserved
