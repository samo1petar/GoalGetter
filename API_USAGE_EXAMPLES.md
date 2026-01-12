# GoalGetter API Usage Examples

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication Flow

### 1. Register a New User

**Endpoint:** `POST /api/v1/auth/signup`

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "name": "John Doe",
    "password": "securepassword123"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "email": "john@example.com",
    "name": "John Doe",
    "id": "6964bffd50693730bf215989",
    "auth_provider": "email",
    "profile_image": null,
    "phase": "goal_setting",
    "meeting_interval": 7,
    "calendar_connected": false,
    "created_at": "2026-01-12T09:33:49.997000",
    "updated_at": "2026-01-12T09:33:49.997000",
    "settings": {
      "meeting_duration": 30,
      "timezone": "UTC",
      "email_notifications": true
    }
  }
}
```

**Save your access token!**
```bash
# Save to variable for easy reuse
export ACCESS_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### 2. Login (Existing User)

**Endpoint:** `POST /api/v1/auth/login`

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "securepassword123"
  }'
```

**Response:** Same as signup (access_token, refresh_token, user)

---

### 3. Get Current User Info

**Endpoint:** `GET /api/v1/auth/me`

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Response:**
```json
{
  "email": "john@example.com",
  "name": "John Doe",
  "id": "6964bffd50693730bf215989",
  "auth_provider": "email",
  "profile_image": null,
  "phase": "goal_setting",
  "meeting_interval": 7,
  "calendar_connected": false,
  "created_at": "2026-01-12T09:33:49.997000",
  "updated_at": "2026-01-12T09:33:49.997000",
  "settings": {
    "meeting_duration": 30,
    "timezone": "UTC",
    "email_notifications": true
  }
}
```

---

### 4. Verify Token is Valid

**Endpoint:** `POST /api/v1/auth/verify-token`

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/verify-token" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Response:**
```json
{
  "valid": true,
  "user": {
    "id": "6964bffd50693730bf215989",
    "email": "john@example.com",
    "name": "John Doe",
    ...
  }
}
```

---

### 5. Refresh Access Token

**Endpoint:** `POST /api/v1/auth/refresh`

When your access token expires (after 30 minutes), use your refresh token to get a new one:

**Request:**
```bash
export REFRESH_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -X POST "http://localhost:8000/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d "{
    \"refresh_token\": \"$REFRESH_TOKEN\"
  }"
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

### 6. Logout

**Endpoint:** `POST /api/v1/auth/logout`

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/logout" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Response:**
```json
{
  "message": "Successfully logged out",
  "detail": "Please discard your access and refresh tokens"
}
```

Note: Currently, logout is client-side (you should delete your tokens). Token blacklisting in Redis will be added later.

---

## Complete Workflow Example

Here's a full example workflow:

```bash
#!/bin/bash

# 1. Register a new user
echo "=== Registering new user ==="
RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "demo@goalgetter.com",
    "name": "Demo User",
    "password": "demo123456"
  }')

echo $RESPONSE | jq .

# 2. Extract access token
ACCESS_TOKEN=$(echo $RESPONSE | jq -r '.access_token')
echo "Access Token: $ACCESS_TOKEN"

# 3. Get user info
echo -e "\n=== Getting user info ==="
curl -s -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq .

# 4. Verify token
echo -e "\n=== Verifying token ==="
curl -s -X POST "http://localhost:8000/api/v1/auth/verify-token" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq .

# 5. Login with same credentials
echo -e "\n=== Logging in ==="
curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "demo@goalgetter.com",
    "password": "demo123456"
  }' | jq .
```

---

## Google OAuth Flow (When Configured)

### 1. Get OAuth URL

**Endpoint:** `GET /api/v1/auth/google`

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/auth/google"
```

**Response:**
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=..."
}
```

### 2. User Authenticates

- Open the `auth_url` in a browser
- User signs in with Google
- Google redirects to callback URL with authorization code

### 3. Backend Handles Callback

**Endpoint:** `GET /api/v1/auth/google/callback?code=...&state=...`

This happens automatically and returns tokens + user info.

---

## Error Responses

### Invalid Credentials
```json
{
  "detail": "Incorrect email or password"
}
```

### Missing Token
```json
{
  "detail": "Not authenticated"
}
```

### Invalid Token
```json
{
  "detail": "Could not validate credentials"
}
```

### User Already Exists
```json
{
  "detail": "Email already registered"
}
```

---

## Health Check & Status

### Health Check
```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "app": "GoalGetter",
  "version": "v1"
}
```

### App Status
```bash
curl http://localhost:8000/status
```

Response:
```json
{
  "app": "GoalGetter",
  "version": "v1",
  "environment": "development",
  "status": "operational",
  "features": {
    "calendar_sync": true,
    "email_notifications": true,
    "pdf_export": true
  }
}
```

---

## Tips & Best Practices

### 1. Store Tokens Securely
```javascript
// In a frontend app (React, Vue, etc.)
localStorage.setItem('access_token', response.access_token);
localStorage.setItem('refresh_token', response.refresh_token);
```

### 2. Auto-Refresh Tokens
When you get a 401 error, automatically refresh:
```javascript
async function apiCall(endpoint) {
  let response = await fetch(endpoint, {
    headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
  });

  if (response.status === 401) {
    // Token expired, refresh it
    const refreshResponse = await fetch('/api/v1/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: localStorage.getItem('refresh_token') })
    });

    const { access_token } = await refreshResponse.json();
    localStorage.setItem('access_token', access_token);

    // Retry original request
    response = await fetch(endpoint, {
      headers: { 'Authorization': `Bearer ${access_token}` }
    });
  }

  return response;
}
```

### 3. Use Pretty JSON with jq
```bash
# Install jq if not available
sudo apt install jq

# Use it with curl
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq .
```

### 4. Save Common Requests
Create a `requests.sh` file:
```bash
#!/bin/bash
export BASE_URL="http://localhost:8000/api/v1"
export ACCESS_TOKEN="your-token-here"

alias api-me="curl -s $BASE_URL/auth/me -H 'Authorization: Bearer $ACCESS_TOKEN' | jq ."
alias api-verify="curl -s -X POST $BASE_URL/auth/verify-token -H 'Authorization: Bearer $ACCESS_TOKEN' | jq ."
```

Then:
```bash
source requests.sh
api-me
api-verify
```

---

## Next Steps

Once Sprint 2 is implemented, you'll have these additional endpoints:

- `GET /api/v1/goals` - List all goals
- `POST /api/v1/goals` - Create a new goal
- `GET /api/v1/goals/{id}` - Get specific goal
- `PUT /api/v1/goals/{id}` - Update goal
- `DELETE /api/v1/goals/{id}` - Delete goal
- `GET /api/v1/goals/{id}/export` - Export goal as PDF

And many more in future sprints!

---

## Interactive Testing

**Swagger UI:** http://localhost:8000/api/v1/docs
**ReDoc:** http://localhost:8000/api/v1/redoc

Both provide interactive API documentation where you can test all endpoints directly in your browser!
