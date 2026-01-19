#!/bin/bash

# GoalGetter Startup Script
# This script starts all services in the correct order

set -e

echo "========================================"
echo "  GoalGetter - Starting Application"
echo "========================================"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker is not running. Please start Docker first."
    exit 1
fi

# Navigate to project directory
cd "$(dirname "$0")"

echo "[1/4] Starting backend services (MongoDB, Redis, Backend)..."
docker compose up -d

echo ""
echo "[2/4] Waiting for backend to be ready..."
echo "      This may take 30-60 seconds on first run..."

# Wait for backend to be ready
max_attempts=30
attempt=1
while [ $attempt -le $max_attempts ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo ""
        echo "      ✓ Backend is ready!"
        break
    fi
    printf "      Waiting for backend... (%d/%d)\r" $attempt $max_attempts
    sleep 2
    attempt=$((attempt + 1))
done

if [ $attempt -gt $max_attempts ]; then
    echo ""
    echo "ERROR: Backend failed to start. Check logs with: docker compose logs backend"
    exit 1
fi

echo ""
echo "[3/4] Installing frontend dependencies (if needed)..."
cd frontend
if [ ! -d "node_modules" ]; then
    npm install
else
    echo "      Dependencies already installed."
fi

echo ""
echo "[4/4] Starting frontend..."
npm run dev > /tmp/goalgetter-frontend.log 2>&1 &
FRONTEND_PID=$!

# Wait for frontend to be ready
echo "      Waiting for frontend to be ready..."
max_attempts=20
attempt=1
while [ $attempt -le $max_attempts ]; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo ""
        echo "      ✓ Frontend is ready!"
        break
    fi
    printf "      Waiting for frontend... (%d/%d)\r" $attempt $max_attempts
    sleep 2
    attempt=$((attempt + 1))
done

if [ $attempt -gt $max_attempts ]; then
    echo ""
    echo "ERROR: Frontend failed to start. Check logs at: /tmp/goalgetter-frontend.log"
    exit 1
fi

echo ""
echo "========================================"
echo "  ✓ GoalGetter is running!"
echo "========================================"
echo ""
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/api/v1/docs"
echo ""
echo "  To stop: Run ./stop.sh or press Ctrl+C"
echo "========================================"
echo ""

# Wait for frontend process (keeps script running)
wait $FRONTEND_PID
