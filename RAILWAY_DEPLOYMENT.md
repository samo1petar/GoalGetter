# GoalGetter Railway Deployment Guide

This guide covers deploying GoalGetter to Railway with GitHub integration.

## Architecture Overview

GoalGetter consists of the following services:

| Service | Description | Railway Service Type |
|---------|-------------|---------------------|
| **Backend** | FastAPI REST/WebSocket API | Docker (from `backend/`) |
| **Frontend** | Next.js web application | Docker (from `frontend/`) |
| **MongoDB** | Primary database | Railway Plugin or MongoDB Atlas |
| **Redis** | Cache, rate limiting, Celery broker | Railway Plugin or Redis Cloud |
| **Celery Worker** | Background job processing | Docker (optional) |

## Prerequisites

1. A [Railway](https://railway.app) account
2. A GitHub account with this repository
3. API keys ready:
   - Anthropic API key (for AI coaching)
   - Google OAuth credentials (for Google login/calendar)
   - SendGrid API key (for emails)

## Deployment Steps

### Step 1: Create Railway Project

1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Click **New Project**
3. Select **Empty Project** (we'll add services manually for proper monorepo support)

### Step 2: Add Database Services

#### Option A: Railway Plugins (Recommended for simplicity)

1. In your Railway project, click **New**
2. Select **Database** → **MongoDB**
3. Repeat for **Redis**

Railway will automatically provide connection URLs.

#### Option B: External Services (Recommended for production)

- **MongoDB Atlas**: Create a free M0 cluster at [mongodb.com/atlas](https://mongodb.com/atlas)
- **Redis Cloud**: Create a free instance at [redis.com/cloud](https://redis.com/cloud)

### Step 3: Deploy Backend Service

1. In your empty project, click **New** → **GitHub Repo**
2. Connect your GitHub account if not already connected
3. Select the `GoalGetter` repository
4. **IMPORTANT**: Click **Add Root Directory** and enter `backend`
5. Click **Deploy** - Railway will detect the Dockerfile in `backend/`

> **Note**: You must set the root directory BEFORE deploying, otherwise Railway looks for a Dockerfile at the repository root and fails.

#### Backend Environment Variables

In the backend service settings, add these variables:

```env
# Application
APP_NAME=GoalGetter
APP_ENV=production
DEBUG=false
API_VERSION=v1

# Security (generate secure random strings, min 32 chars)
SECRET_KEY=<generate-with: openssl rand -hex 32>
JWT_SECRET_KEY=<generate-with: openssl rand -hex 32>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Database (use Railway variable references for plugins)
MONGODB_URI=${{MongoDB.MONGO_URL}}/goalgetter
MONGODB_DB_NAME=goalgetter
MONGODB_MIN_POOL_SIZE=5
MONGODB_MAX_POOL_SIZE=20

# Redis (use Railway variable references for plugins)
REDIS_URL=${{Redis.REDIS_URL}}
REDIS_MAX_CONNECTIONS=20

# Anthropic Claude API
ANTHROPIC_API_KEY=<your-anthropic-api-key>
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_MAX_TOKENS=4096
ANTHROPIC_TEMPERATURE=0.7

# Google OAuth
GOOGLE_CLIENT_ID=<your-google-client-id>
GOOGLE_CLIENT_SECRET=<your-google-client-secret>
GOOGLE_REDIRECT_URI=https://<your-backend-url>/api/v1/auth/google/callback

# Email - SendGrid
SENDGRID_API_KEY=<your-sendgrid-api-key>
FROM_EMAIL=noreply@yourdomain.com
FROM_NAME=GoalGetter
SUPPORT_EMAIL=support@yourdomain.com

# Frontend URL (for CORS and OAuth redirects)
FRONTEND_URL=https://<your-frontend-url>
BACKEND_CORS_ORIGINS=https://<your-frontend-url>

# Celery (if using background jobs)
CELERY_BROKER_URL=${{Redis.REDIS_URL}}/1
CELERY_RESULT_BACKEND=${{Redis.REDIS_URL}}/2

# Feature Flags
ENABLE_CALENDAR_SYNC=true
ENABLE_EMAIL_NOTIFICATIONS=true
ENABLE_PDF_EXPORT=true

# Monitoring (optional)
SENTRY_DSN=<your-sentry-dsn>
SENTRY_ENVIRONMENT=production

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Step 4: Deploy Frontend Service

1. Click **New** → **GitHub Repo** → Select `GoalGetter`
2. **IMPORTANT**: Click **Add Root Directory** and enter `frontend`
3. Click **Deploy** - Railway will detect the Dockerfile in `frontend/`

#### Frontend Environment Variables

```env
# Backend API URL (use Railway variable reference)
NEXT_PUBLIC_API_URL=https://${{Backend.RAILWAY_PUBLIC_DOMAIN}}
```

**Important**: The `NEXT_PUBLIC_API_URL` must be set as a **build argument** because Next.js bakes public environment variables at build time.

To set build args in Railway:
1. Go to frontend service **Settings**
2. Under **Build**, find **Build Arguments**
3. Add: `NEXT_PUBLIC_API_URL=https://your-backend-url.railway.app`

### Step 5: Configure Networking

1. For each service, go to **Settings** → **Networking**
2. Click **Generate Domain** to create a public URL
3. Alternatively, add a **Custom Domain** if you have one

### Step 6: Deploy Celery Worker (Optional)

If you need background job processing:

1. Click **New** → **GitHub Repo** → Select `GoalGetter`
2. Set **Root Directory** to `backend`
3. In service settings, set **Start Command**:
   ```
   celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2
   ```
4. Copy all backend environment variables to this service

### Step 7: Set Up GitHub Integration

Railway automatically deploys on push to your default branch. To configure:

1. Go to project **Settings** → **Deployments**
2. Configure branch triggers (e.g., `main` or `master`)
3. Enable/disable automatic deployments as needed

## Post-Deployment Checklist

- [ ] Verify backend health: `https://your-backend-url/health`
- [ ] Verify frontend loads: `https://your-frontend-url`
- [ ] Test user registration and login
- [ ] Test Google OAuth flow
- [ ] Test AI chat functionality
- [ ] Update Google OAuth redirect URI in Google Cloud Console
- [ ] Configure custom domains (optional)
- [ ] Set up monitoring/alerts in Railway

## Environment Variable Reference

### Using Railway Variable References

Railway supports referencing variables from other services:

```env
# Reference MongoDB plugin
MONGODB_URI=${{MongoDB.MONGO_URL}}

# Reference Redis plugin
REDIS_URL=${{Redis.REDIS_URL}}

# Reference another service's domain
NEXT_PUBLIC_API_URL=https://${{Backend.RAILWAY_PUBLIC_DOMAIN}}
```

### Generating Secrets

Generate secure secrets for production:

```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate JWT_SECRET_KEY
openssl rand -hex 32
```

## Scaling

### Horizontal Scaling

In Railway service settings:
- Increase **Replicas** for the backend/frontend
- Note: Requires proper session handling for multiple replicas

### Vertical Scaling

Railway automatically scales resources. For manual control:
- Set memory/CPU limits in service settings
- Adjust worker counts in start commands

## Troubleshooting

### Build Failures

**"Dockerfile does not exist" error:**
- This means Railway is looking at the wrong directory
- Go to service **Settings** → **Source** → **Root Directory**
- Set it to `backend` or `frontend` as appropriate
- Trigger a new deployment

**General build failures:**
1. Check build logs in Railway dashboard
2. Ensure all environment variables are set
3. Verify Dockerfile paths are correct

### Connection Issues

1. Check MongoDB/Redis connection strings
2. Verify CORS origins include frontend URL
3. Check Railway service networking settings

### Health Check Failures

1. Backend health endpoint: `/health`
2. Frontend health endpoint: `/`
3. Increase `healthcheckTimeout` if needed

## Cost Optimization

- Use Railway's **Hobby** plan for development
- MongoDB Atlas M0 and Redis Cloud free tiers for databases
- Scale down replicas during low-traffic periods

## Security Notes

1. Never commit `.env` files with real secrets
2. Use Railway's secret management for sensitive values
3. Enable HTTPS (Railway provides this automatically)
4. Regularly rotate API keys and secrets
5. Monitor for unusual activity in Railway metrics

## Support

- Railway Documentation: https://docs.railway.app
- GoalGetter Issues: https://github.com/your-repo/issues
