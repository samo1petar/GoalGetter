# GoalGetter Deployment Guide

This guide covers deploying GoalGetter to production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Configuration](#environment-configuration)
3. [Docker Deployment](#docker-deployment)
4. [Cloud Deployment Options](#cloud-deployment-options)
5. [Database Setup](#database-setup)
6. [SSL/TLS Configuration](#ssltls-configuration)
7. [Monitoring and Logging](#monitoring-and-logging)
8. [Backup and Recovery](#backup-and-recovery)
9. [Scaling](#scaling)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before deploying, ensure you have:

- Docker and Docker Compose installed
- Domain name configured (for production)
- SSL certificates (Let's Encrypt recommended)
- External service accounts:
  - **Anthropic API key** (required for AI coaching)
  - **SendGrid API key** (optional, for email notifications)
  - **Google OAuth credentials** (optional, for OAuth login)
  - **Sentry DSN** (optional, for error monitoring)

---

## Environment Configuration

### Required Environment Variables

Create a `.env` file with the following required variables:

```bash
# Application
APP_ENV=production
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=json

# Security (generate strong random values)
SECRET_KEY=<generate-with-openssl-rand-hex-32>
JWT_SECRET_KEY=<generate-with-openssl-rand-hex-32>

# Database
MONGO_ROOT_USERNAME=admin
MONGO_ROOT_PASSWORD=<strong-password>
REDIS_PASSWORD=<strong-password>

# External Services
ANTHROPIC_API_KEY=sk-ant-your-api-key
```

### Optional Environment Variables

```bash
# Google OAuth
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret

# Email (SendGrid)
SENDGRID_API_KEY=SG.your-api-key
FROM_EMAIL=noreply@yourdomain.com

# Monitoring (Sentry)
SENTRY_DSN=https://your-sentry-dsn
SENTRY_ENVIRONMENT=production

# CORS (comma-separated list)
BACKEND_CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### Generate Secrets

```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate JWT_SECRET_KEY
openssl rand -hex 32

# Generate database passwords
openssl rand -base64 24
```

---

## Docker Deployment

### Production Deployment

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-org/goalgetter.git
   cd goalgetter
   ```

2. **Create environment file:**
   ```bash
   cp backend/.env.example .env
   # Edit .env with production values
   ```

3. **Deploy with Docker Compose:**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

4. **Verify deployment:**
   ```bash
   # Check all services are running
   docker-compose -f docker-compose.prod.yml ps

   # Check logs
   docker-compose -f docker-compose.prod.yml logs -f backend

   # Test health endpoint
   curl http://localhost:8000/health
   ```

### With Nginx (SSL Termination)

1. **Create Nginx configuration:**
   ```bash
   mkdir -p nginx/ssl
   ```

2. **Create `nginx/nginx.conf`:**
   ```nginx
   events {
       worker_connections 1024;
   }

   http {
       upstream backend {
           server backend:8000;
       }

       # Redirect HTTP to HTTPS
       server {
           listen 80;
           server_name yourdomain.com;
           return 301 https://$server_name$request_uri;
       }

       # HTTPS server
       server {
           listen 443 ssl http2;
           server_name yourdomain.com;

           ssl_certificate /etc/nginx/ssl/fullchain.pem;
           ssl_certificate_key /etc/nginx/ssl/privkey.pem;

           # SSL settings
           ssl_protocols TLSv1.2 TLSv1.3;
           ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
           ssl_prefer_server_ciphers off;

           # Security headers
           add_header X-Frame-Options "SAMEORIGIN" always;
           add_header X-Content-Type-Options "nosniff" always;
           add_header X-XSS-Protection "1; mode=block" always;

           location / {
               proxy_pass http://backend;
               proxy_set_header Host $host;
               proxy_set_header X-Real-IP $remote_addr;
               proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
               proxy_set_header X-Forwarded-Proto $scheme;
           }

           # WebSocket support
           location /api/v1/chat/ws {
               proxy_pass http://backend;
               proxy_http_version 1.1;
               proxy_set_header Upgrade $http_upgrade;
               proxy_set_header Connection "upgrade";
               proxy_set_header Host $host;
               proxy_read_timeout 86400;
           }
       }
   }
   ```

3. **Deploy with Nginx:**
   ```bash
   docker-compose -f docker-compose.prod.yml --profile with-nginx up -d
   ```

---

## Cloud Deployment Options

### Option 1: Railway (Recommended for Simplicity)

1. **Push to GitHub**
2. **Connect Railway to repository**
3. **Add services:**
   - MongoDB (Railway plugin)
   - Redis (Railway plugin)
4. **Configure environment variables**
5. **Deploy**

Railway automatically detects the Dockerfile and handles deployment.

### Option 2: AWS (ECS/Fargate)

1. **Create ECR repositories:**
   ```bash
   aws ecr create-repository --repository-name goalgetter-backend
   ```

2. **Build and push images:**
   ```bash
   docker build -t goalgetter-backend ./backend
   aws ecr get-login-password | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com
   docker tag goalgetter-backend:latest <account>.dkr.ecr.<region>.amazonaws.com/goalgetter-backend:latest
   docker push <account>.dkr.ecr.<region>.amazonaws.com/goalgetter-backend:latest
   ```

3. **Deploy ECS task definitions and services**

### Option 3: Google Cloud Run

1. **Build and push to GCR:**
   ```bash
   gcloud builds submit --tag gcr.io/PROJECT_ID/goalgetter-backend ./backend
   ```

2. **Deploy to Cloud Run:**
   ```bash
   gcloud run deploy goalgetter-backend \
     --image gcr.io/PROJECT_ID/goalgetter-backend \
     --platform managed \
     --allow-unauthenticated
   ```

### Option 4: DigitalOcean App Platform

1. Connect GitHub repository
2. Configure environment variables
3. Select resources (Basic $5/mo plan works for testing)
4. Deploy

---

## Database Setup

### MongoDB Atlas (Recommended for Production)

1. **Create cluster** at [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. **Configure network access** (allow your server IPs)
3. **Create database user**
4. **Get connection string:**
   ```
   MONGODB_URI=mongodb+srv://<user>:<password>@cluster.mongodb.net/goalgetter?retryWrites=true&w=majority
   ```

### Redis Cloud

1. **Create database** at [Redis Cloud](https://redis.com/try-free/)
2. **Get connection string:**
   ```
   REDIS_URL=redis://:<password>@<host>:<port>
   ```

### Database Indexes

Ensure these indexes are created for optimal performance:

```javascript
// MongoDB indexes
db.users.createIndex({ "email": 1 }, { unique: true })
db.goals.createIndex({ "user_id": 1, "created_at": -1 })
db.meetings.createIndex({ "user_id": 1, "scheduled_at": 1 })
db.chat_messages.createIndex({ "user_id": 1, "timestamp": -1 })
```

---

## SSL/TLS Configuration

### Using Let's Encrypt with Certbot

```bash
# Install certbot
apt-get install certbot python3-certbot-nginx

# Obtain certificate
certbot --nginx -d yourdomain.com

# Auto-renewal
certbot renew --dry-run
```

### Certificate Locations

```
/etc/letsencrypt/live/yourdomain.com/fullchain.pem
/etc/letsencrypt/live/yourdomain.com/privkey.pem
```

---

## Monitoring and Logging

### Sentry Integration

1. **Create project** at [Sentry](https://sentry.io)
2. **Add DSN to environment:**
   ```
   SENTRY_DSN=https://xxx@sentry.io/xxx
   ```

### Log Aggregation

Production logs are in JSON format. Use these tools:

- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Datadog**
- **CloudWatch Logs** (AWS)
- **Cloud Logging** (GCP)

### Health Checks

```bash
# API health
curl https://yourdomain.com/health

# Detailed status
curl https://yourdomain.com/status
```

### Celery Monitoring (Flower)

Access Flower UI at `http://localhost:5555` (not exposed in production by default).

---

## Backup and Recovery

### MongoDB Backups

```bash
# Create backup
mongodump --uri="$MONGODB_URI" --out=/backups/$(date +%Y%m%d)

# Restore backup
mongorestore --uri="$MONGODB_URI" /backups/20240112
```

### Automated Backups (Cron)

```bash
# Add to crontab
0 2 * * * /usr/local/bin/backup-mongodb.sh
```

### Redis Persistence

Redis is configured with AOF persistence. RDB snapshots are also recommended:

```bash
# In redis.conf
save 900 1
save 300 10
save 60 10000
```

---

## Scaling

### Horizontal Scaling

1. **Backend:** Increase `--workers` in uvicorn command or add more containers
2. **Celery:** Add more worker containers
3. **Redis:** Use Redis Cluster for high availability
4. **MongoDB:** Use replica sets for high availability

### Load Balancing

Use nginx or cloud load balancers:

```nginx
upstream backend {
    least_conn;
    server backend1:8000;
    server backend2:8000;
    server backend3:8000;
}
```

### Docker Swarm/Kubernetes

For larger deployments, consider:

- Docker Swarm for simple orchestration
- Kubernetes for complex deployments

---

## Troubleshooting

### Common Issues

**1. Container won't start:**
```bash
docker-compose -f docker-compose.prod.yml logs backend
```

**2. Database connection failed:**
- Check `MONGODB_URI` format
- Verify network access rules
- Check credentials

**3. WebSocket connection issues:**
- Verify nginx proxy configuration
- Check firewall rules for WebSocket ports

**4. Rate limiting errors:**
- Check Redis connection
- Verify `REDIS_URL` is correct

### Debug Mode

Temporarily enable debug mode (NOT for production traffic):

```bash
DEBUG=true docker-compose -f docker-compose.prod.yml up backend
```

### Logs

```bash
# All logs
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f backend

# Last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100 backend
```

---

## Security Checklist

Before going live, ensure:

- [ ] Strong passwords for all services
- [ ] SSL/TLS configured
- [ ] CORS origins restricted to your domains
- [ ] Rate limiting enabled
- [ ] Debug mode disabled
- [ ] Sentry configured for error monitoring
- [ ] Database backups configured
- [ ] Firewall rules configured
- [ ] Environment variables not exposed
- [ ] API keys rotated from development

---

## Support

For deployment issues:
- Create an issue in the repository
- Contact: support@goalgetter.com
