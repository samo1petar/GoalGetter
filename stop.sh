#!/bin/bash

# GoalGetter Stop Script

echo "Stopping GoalGetter..."

# Stop frontend
pkill -f "next dev" 2>/dev/null || true

# Stop Docker services
cd "$(dirname "$0")"
docker compose down

echo "GoalGetter stopped."
