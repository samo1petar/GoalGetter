#!/bin/bash

# GoalGetter API Helper Script
# Makes it easy to interact with the API from command line

BASE_URL="http://localhost:8000/api/v1"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

function show_help() {
    echo "GoalGetter API Helper"
    echo ""
    echo "Usage: ./api-helper.sh [command] [options]"
    echo ""
    echo "Commands:"
    echo "  signup <email> <name> <password>    Register a new user"
    echo "  login <email> <password>            Login and save token"
    echo "  me                                  Get current user info"
    echo "  verify                              Verify current token"
    echo "  health                              Check API health"
    echo "  docs                                Open API documentation"
    echo ""
    echo "Examples:"
    echo "  ./api-helper.sh signup john@test.com 'John Doe' mypass123"
    echo "  ./api-helper.sh login john@test.com mypass123"
    echo "  ./api-helper.sh me"
    echo ""
}

function signup() {
    if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
        echo -e "${RED}Error: Missing arguments${NC}"
        echo "Usage: ./api-helper.sh signup <email> <name> <password>"
        exit 1
    fi

    echo -e "${BLUE}Registering user: $1${NC}"

    RESPONSE=$(curl -s -X POST "$BASE_URL/auth/signup" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"$1\",\"name\":\"$2\",\"password\":\"$3\"}")

    if echo "$RESPONSE" | jq -e '.access_token' > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Registration successful!${NC}"
        ACCESS_TOKEN=$(echo $RESPONSE | jq -r '.access_token')
        echo $ACCESS_TOKEN > ~/.goalgetter_token
        echo ""
        echo "User: $(echo $RESPONSE | jq -r '.user.name')"
        echo "Email: $(echo $RESPONSE | jq -r '.user.email')"
        echo "Phase: $(echo $RESPONSE | jq -r '.user.phase')"
        echo ""
        echo "Token saved to ~/.goalgetter_token"
    else
        echo -e "${RED}✗ Registration failed${NC}"
        echo $RESPONSE | jq -r '.detail'
    fi
}

function login() {
    if [ -z "$1" ] || [ -z "$2" ]; then
        echo -e "${RED}Error: Missing arguments${NC}"
        echo "Usage: ./api-helper.sh login <email> <password>"
        exit 1
    fi

    echo -e "${BLUE}Logging in: $1${NC}"

    RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"$1\",\"password\":\"$2\"}")

    if echo "$RESPONSE" | jq -e '.access_token' > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Login successful!${NC}"
        ACCESS_TOKEN=$(echo $RESPONSE | jq -r '.access_token')
        echo $ACCESS_TOKEN > ~/.goalgetter_token
        echo ""
        echo "User: $(echo $RESPONSE | jq -r '.user.name')"
        echo "Email: $(echo $RESPONSE | jq -r '.user.email')"
        echo ""
        echo "Token saved to ~/.goalgetter_token"
    else
        echo -e "${RED}✗ Login failed${NC}"
        echo $RESPONSE | jq -r '.detail'
    fi
}

function get_me() {
    if [ ! -f ~/.goalgetter_token ]; then
        echo -e "${RED}Error: No token found. Please login first.${NC}"
        exit 1
    fi

    ACCESS_TOKEN=$(cat ~/.goalgetter_token)

    echo -e "${BLUE}Fetching user profile...${NC}"

    RESPONSE=$(curl -s -X GET "$BASE_URL/auth/me" \
        -H "Authorization: Bearer $ACCESS_TOKEN")

    if echo "$RESPONSE" | jq -e '.email' > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Profile retrieved${NC}"
        echo ""
        echo $RESPONSE | jq .
    else
        echo -e "${RED}✗ Failed to get profile${NC}"
        echo "Try logging in again"
    fi
}

function verify_token() {
    if [ ! -f ~/.goalgetter_token ]; then
        echo -e "${RED}Error: No token found. Please login first.${NC}"
        exit 1
    fi

    ACCESS_TOKEN=$(cat ~/.goalgetter_token)

    echo -e "${BLUE}Verifying token...${NC}"

    RESPONSE=$(curl -s -X POST "$BASE_URL/auth/verify-token" \
        -H "Authorization: Bearer $ACCESS_TOKEN")

    VALID=$(echo $RESPONSE | jq -r '.valid')

    if [ "$VALID" = "true" ]; then
        echo -e "${GREEN}✓ Token is valid${NC}"
        echo "User: $(echo $RESPONSE | jq -r '.user.name')"
    else
        echo -e "${RED}✗ Token is invalid or expired${NC}"
        echo "Please login again"
    fi
}

function check_health() {
    echo -e "${BLUE}Checking API health...${NC}"

    RESPONSE=$(curl -s http://localhost:8000/health)

    STATUS=$(echo $RESPONSE | jq -r '.status')

    if [ "$STATUS" = "healthy" ]; then
        echo -e "${GREEN}✓ API is healthy${NC}"
        echo $RESPONSE | jq .
    else
        echo -e "${RED}✗ API is not responding${NC}"
    fi
}

function open_docs() {
    echo "Opening API documentation..."
    if command -v xdg-open > /dev/null; then
        xdg-open "http://localhost:8000/api/v1/docs"
    elif command -v open > /dev/null; then
        open "http://localhost:8000/api/v1/docs"
    else
        echo "Please open in browser: http://localhost:8000/api/v1/docs"
    fi
}

# Main command handler
case "$1" in
    signup)
        signup "$2" "$3" "$4"
        ;;
    login)
        login "$2" "$3"
        ;;
    me)
        get_me
        ;;
    verify)
        verify_token
        ;;
    health)
        check_health
        ;;
    docs)
        open_docs
        ;;
    *)
        show_help
        ;;
esac
