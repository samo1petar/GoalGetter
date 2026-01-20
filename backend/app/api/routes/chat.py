"""
Chat API routes including WebSocket endpoint for real-time AI coaching.
Implements Tony Robbins persona with chat access control.
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from bson import ObjectId
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.database import get_database
from app.core.security import SecurityUtils, get_current_active_user
from app.core.websocket_manager import connection_manager, get_connection_manager
from app.services.llm import LLMServiceFactory, LLMProvider
from app.services.goal_tool_handler import GoalToolHandler
from app.models.message import MessageModel
from app.models.goal import GoalModel
from app.schemas.chat import (
    ChatHistoryResponse,
    ChatAccessResponse,
    MessageResponse,
    ClearHistoryResponse,
    WebSocketMessage,
    ProviderResponse,
    AvailableProvidersResponse,
    ProviderInfo,
    SetProviderRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()

# Rate limiter for chat endpoints
limiter = Limiter(key_func=get_remote_address)


# Chat Access Control
class ChatAccessControl:
    """
    Controls chat access based on user phase and meeting status.

    - Goal Setting Phase: Always allow access
    - Tracking Phase: Only during active meeting windows
    """

    MEETING_WINDOW_BEFORE_MINUTES = settings.MEETING_WINDOW_BEFORE_MINUTES
    MEETING_WINDOW_AFTER_MINUTES = settings.MEETING_WINDOW_AFTER_MINUTES

    @staticmethod
    async def can_access_chat(
        user_id: str,
        user_phase: str,
        db,
    ) -> Dict[str, Any]:
        """
        Determine if user can access chat based on their phase and meeting status.

        Args:
            user_id: The user's ID
            user_phase: The user's current phase ("goal_setting" or "tracking")
            db: Database instance

        Returns:
            Dict with can_access, reason, and optional next_available/meeting_id
        """
        # Goal Setting Phase: Always allow access
        if user_phase == "goal_setting":
            return {
                "can_access": True,
                "reason": "Goal setting phase - unlimited coach access",
                "user_phase": user_phase,
                "next_available": None,
                "meeting_id": None,
            }

        # Tracking Phase: Check for active meeting
        if user_phase == "tracking":
            current_time = datetime.utcnow()

            # Calculate window boundaries
            window_start = current_time - timedelta(
                minutes=ChatAccessControl.MEETING_WINDOW_BEFORE_MINUTES
            )

            # Find active or upcoming meeting within window
            meeting = await db.meetings.find_one({
                "user_id": ObjectId(user_id),
                "status": {"$in": ["scheduled", "active"]},
                "scheduled_at": {
                    "$gte": window_start,
                    "$lte": current_time + timedelta(hours=2),
                }
            })

            if meeting:
                meeting_start = meeting["scheduled_at"]
                duration = meeting.get("duration_minutes", settings.DEFAULT_MEETING_DURATION_MINUTES)

                # Calculate meeting window
                window_open = meeting_start - timedelta(
                    minutes=ChatAccessControl.MEETING_WINDOW_BEFORE_MINUTES
                )
                window_close = meeting_start + timedelta(
                    minutes=duration + ChatAccessControl.MEETING_WINDOW_AFTER_MINUTES
                )

                # Check if current time is within meeting window
                if window_open <= current_time <= window_close:
                    return {
                        "can_access": True,
                        "reason": "Active meeting window",
                        "user_phase": user_phase,
                        "next_available": None,
                        "meeting_id": str(meeting["_id"]),
                    }

            # No active meeting - find next scheduled meeting
            next_meeting = await db.meetings.find_one(
                {
                    "user_id": ObjectId(user_id),
                    "status": "scheduled",
                    "scheduled_at": {"$gt": current_time},
                },
                sort=[("scheduled_at", 1)],
            )

            next_available = None
            if next_meeting:
                next_available = (
                    next_meeting["scheduled_at"] -
                    timedelta(minutes=ChatAccessControl.MEETING_WINDOW_BEFORE_MINUTES)
                ).isoformat()

            return {
                "can_access": False,
                "reason": "Chat is only available during scheduled meetings in tracking phase",
                "user_phase": user_phase,
                "next_available": next_available,
                "meeting_id": None,
            }

        # Unknown phase
        return {
            "can_access": False,
            "reason": "Invalid user phase",
            "user_phase": user_phase,
            "next_available": None,
            "meeting_id": None,
        }


# Helper function to get user from token for WebSocket
async def get_user_from_token(token: str, db) -> Optional[Dict[str, Any]]:
    """
    Validate token and get user for WebSocket authentication.

    Args:
        token: JWT access token
        db: Database instance

    Returns:
        User dict if valid, None otherwise
    """
    try:
        payload = SecurityUtils.verify_token(token, token_type="access")
        user_id = payload.get("user_id")

        if not user_id:
            return None

        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return None

        from app.models.user import UserModel
        return UserModel.serialize_user(user)

    except Exception as e:
        logger.warning(f"Token validation failed: {e}")
        return None


# Helper function to get user's goals
async def get_user_goals(user_id: str, db, limit: int = 5) -> List[Dict[str, Any]]:
    """Get user's goals for context injection."""
    cursor = db.goals.find(
        {"user_id": ObjectId(user_id), "phase": {"$ne": "archived"}},
        sort=[("updated_at", -1)],
        limit=limit,
    )
    goals = await cursor.to_list(length=limit)
    return [GoalModel.serialize_goal(g) for g in goals]


# Helper function to get conversation history
async def get_conversation_history(
    user_id: str,
    db,
    limit: int = 10,
    meeting_id: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Get recent conversation history for context."""
    query = {"user_id": ObjectId(user_id)}
    if meeting_id:
        query["meeting_id"] = ObjectId(meeting_id)

    cursor = db.chat_messages.find(
        query,
        sort=[("timestamp", -1)],
        limit=limit,
    )
    messages = await cursor.to_list(length=limit)

    # Reverse to get chronological order and format for Claude
    return MessageModel.to_chat_history_format(list(reversed(messages)))


# REST API Endpoints

@router.get("/access", response_model=ChatAccessResponse)
@limiter.limit("30/minute")  # Frequent access checks allowed
async def check_chat_access(
    request: Request,
    current_user: dict = Depends(get_current_active_user),
    db=Depends(get_database),
):
    """
    Check if the current user can access the chat.

    Returns access status based on user phase and meeting status.
    Rate limit: 30 requests per minute.
    """
    result = await ChatAccessControl.can_access_chat(
        user_id=current_user["id"],
        user_phase=current_user["phase"],
        db=db,
    )
    return ChatAccessResponse(**result)


@router.get("/history", response_model=ChatHistoryResponse)
@limiter.limit("30/minute")
async def get_chat_history(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    meeting_id: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user),
    db=Depends(get_database),
):
    """
    Get chat message history for the current user.

    Supports pagination and optional filtering by meeting_id.
    """
    user_id = current_user["id"]
    skip = (page - 1) * page_size

    # Build query
    query = {"user_id": ObjectId(user_id)}
    if meeting_id:
        query["meeting_id"] = ObjectId(meeting_id)

    # Get total count
    total = await db.chat_messages.count_documents(query)

    # Get messages with pagination
    cursor = db.chat_messages.find(
        query,
        sort=[("timestamp", -1)],
        skip=skip,
        limit=page_size,
    )
    messages = await cursor.to_list(length=page_size)

    # Serialize and reverse to get chronological order
    serialized = MessageModel.serialize_messages(list(reversed(messages)))

    return ChatHistoryResponse(
        messages=serialized,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(skip + len(messages)) < total,
    )


@router.delete("/history", response_model=ClearHistoryResponse)
async def clear_chat_history(
    meeting_id: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user),
    db=Depends(get_database),
):
    """
    Clear chat history for the current user.

    Optionally clear only messages from a specific meeting.
    """
    user_id = current_user["id"]

    # Build query
    query = {"user_id": ObjectId(user_id)}
    if meeting_id:
        query["meeting_id"] = ObjectId(meeting_id)

    # Delete messages
    result = await db.chat_messages.delete_many(query)

    return ClearHistoryResponse(
        success=True,
        deleted_count=result.deleted_count,
        message=f"Successfully deleted {result.deleted_count} messages",
    )


# Provider Management Endpoints

@router.get("/providers", response_model=AvailableProvidersResponse)
async def get_available_providers(
    current_user: dict = Depends(get_current_active_user),
) -> AvailableProvidersResponse:
    """
    Get list of available LLM providers.

    Returns available providers and the user's current preference.
    """
    available = LLMServiceFactory.get_available_providers()

    providers = []
    for provider_id in ["claude", "openai"]:
        if provider_id == "claude":
            providers.append(ProviderInfo(
                id="claude",
                name="Claude (Anthropic)",
                description="Claude 3.5 Sonnet - Thoughtful, nuanced responses",
                available="claude" in available,
            ))
        elif provider_id == "openai":
            providers.append(ProviderInfo(
                id="openai",
                name="GPT (OpenAI)",
                description="GPT-4o - Fast, capable responses with tracing",
                available="openai" in available,
            ))

    return AvailableProvidersResponse(
        providers=providers,
        current=current_user.get("llm_provider", "claude"),
    )


@router.put("/provider", response_model=ProviderResponse)
async def set_user_provider(
    request: SetProviderRequest,
    current_user: dict = Depends(get_current_active_user),
    db=Depends(get_database),
) -> ProviderResponse:
    """
    Set user's preferred LLM provider.

    Updates the user's default provider for chat interactions.
    """
    provider = request.provider
    available = LLMServiceFactory.get_available_providers()

    if provider not in available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider '{provider}' is not available. Available providers: {available}",
        )

    # Update user's provider preference
    await db.users.update_one(
        {"_id": ObjectId(current_user["id"])},
        {"$set": {"llm_provider": provider}}
    )

    return ProviderResponse(provider=provider)


# WebSocket Endpoint

@router.websocket("/ws")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    db=Depends(get_database),
):
    """
    WebSocket endpoint for real-time chat with the AI coach.

    Authentication is done via query parameter token.
    Messages are streamed from Claude API with Tony Robbins persona.

    Client messages should be JSON: {"type": "message", "content": "..."}
    Server responses are JSON: {"type": "response_chunk|response|error", "content": "...", ...}
    """
    user = None

    try:
        # Authenticate user
        user = await get_user_from_token(token, db)
        if not user:
            await websocket.close(code=4001, reason="Invalid or expired token")
            return

        user_id = user["id"]
        user_phase = user["phase"]

        # Check chat access
        access = await ChatAccessControl.can_access_chat(user_id, user_phase, db)
        if not access["can_access"]:
            await websocket.accept()
            await websocket.send_json({
                "type": "error",
                "content": access["reason"],
                "next_available": access.get("next_available"),
            })
            await websocket.close(code=4003, reason=access["reason"])
            return

        # Connect to WebSocket manager
        connected = await connection_manager.connect(websocket, user_id, user_phase)
        if not connected:
            await websocket.close(code=4000, reason="Failed to establish connection")
            return

        # Send connected confirmation
        await websocket.send_json({
            "type": "connected",
            "content": "Connected to GoalGetter AI Coach",
            "user_phase": user_phase,
            "meeting_id": access.get("meeting_id"),
        })

        # Get user's goals for context
        user_goals = await get_user_goals(user_id, db)
        meeting_id = access.get("meeting_id")

        # Main message loop
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_json()

                # Parse message
                msg_type = data.get("type", "message")
                content = data.get("content", "")

                # Handle ping
                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                    continue

                # Handle typing indicator (just acknowledge)
                if msg_type == "typing":
                    continue

                # Handle message
                if msg_type == "message" and content:
                    # Re-check access (in case phase changed during session)
                    access = await ChatAccessControl.can_access_chat(user_id, user_phase, db)
                    if not access["can_access"]:
                        await websocket.send_json({
                            "type": "error",
                            "content": access["reason"],
                            "next_available": access.get("next_available"),
                        })
                        continue

                    # Parse draft goals from message
                    draft_goals = data.get("draft_goals", [])
                    active_goal_id = data.get("active_goal_id")

                    # Save user message
                    user_message_doc = MessageModel.create_message_document(
                        user_id=user_id,
                        role="user",
                        content=content,
                        meeting_id=meeting_id,
                    )
                    result = await db.chat_messages.insert_one(user_message_doc)
                    user_message_id = str(result.inserted_id)

                    # Send typing indicator
                    await websocket.send_json({
                        "type": "typing",
                        "content": "Coach is thinking...",
                    })

                    # Get conversation history for context
                    history = await get_conversation_history(user_id, db, limit=10, meeting_id=meeting_id)

                    # Initialize tool handler for this session
                    tool_handler = GoalToolHandler(db, user_id)

                    # Get the LLM service (uses DEFAULT_LLM_PROVIDER from config)
                    try:
                        llm_service = LLMServiceFactory.get_service()
                    except ValueError as e:
                        await websocket.send_json({
                            "type": "error",
                            "content": str(e),
                        })
                        continue

                    # Stream response from LLM service
                    full_response = ""
                    tokens_used = 0
                    model_used = None
                    assistant_message_id = None

                    async for chunk in llm_service.stream_message(
                        message=content,
                        conversation_history=history,
                        user_phase=user_phase,
                        user_goals=user_goals,
                        draft_goals=draft_goals,
                        use_tools=True,
                    ):
                        if chunk["type"] == "chunk":
                            full_response += chunk["content"]
                            await websocket.send_json({
                                "type": "response_chunk",
                                "content": chunk["content"],
                                "is_complete": False,
                            })

                        elif chunk["type"] == "tool_call":
                            # Execute the tool
                            tool_name = chunk.get("tool_name")
                            tool_input = chunk.get("tool_input", {})

                            logger.info(f"Executing tool: {tool_name} with input: {tool_input}")

                            # Execute tool and get result
                            tool_result = await tool_handler.execute_tool(
                                tool_name=tool_name,
                                tool_input=tool_input,
                                active_goal_id=active_goal_id,
                            )

                            # Send tool result to frontend
                            await websocket.send_json({
                                "type": "tool_call",
                                "tool": tool_name,
                                "tool_result": tool_result,
                            })

                            # Refresh user goals after tool execution
                            if tool_result.get("success"):
                                user_goals = await get_user_goals(user_id, db)

                        elif chunk["type"] == "complete":
                            tokens_used = chunk.get("tokens_used", 0)
                            model_used = chunk.get("model")

                            # Save assistant message
                            assistant_message_doc = MessageModel.create_message_document(
                                user_id=user_id,
                                role="assistant",
                                content=full_response,
                                meeting_id=meeting_id,
                                model=model_used,
                                tokens_used=tokens_used,
                            )
                            result = await db.chat_messages.insert_one(assistant_message_doc)
                            assistant_message_id = str(result.inserted_id)

                            # Send completion signal
                            await websocket.send_json({
                                "type": "response",
                                "content": full_response,
                                "message_id": assistant_message_id,
                                "is_complete": True,
                                "tokens_used": tokens_used,
                            })

                        elif chunk["type"] == "error":
                            # Save error response as assistant message
                            assistant_message_doc = MessageModel.create_message_document(
                                user_id=user_id,
                                role="assistant",
                                content=chunk["content"],
                                meeting_id=meeting_id,
                            )
                            await db.chat_messages.insert_one(assistant_message_doc)

                            await websocket.send_json({
                                "type": "error",
                                "content": chunk["content"],
                                "error": chunk.get("error"),
                                "is_complete": True,
                            })

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for user {user_id}")
                break
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "content": "Invalid message format. Expected JSON.",
                })
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "content": "An error occurred processing your message.",
                    "error": str(e) if settings.DEBUG else None,
                })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if user:
            await connection_manager.disconnect(websocket)


# HTTP endpoint for sending messages (alternative to WebSocket)
@router.post("/send")
@limiter.limit("30/minute")  # Limit AI requests to control costs
async def send_chat_message(
    request: Request,
    content: str = Query(..., min_length=1, max_length=10000),
    current_user: dict = Depends(get_current_active_user),
    db=Depends(get_database),
):
    """
    Send a message to the AI coach and get a response.

    This is an HTTP alternative to the WebSocket endpoint.
    Does not support streaming - returns complete response.
    Rate limit: 30 requests per minute to control API costs.
    """
    user_id = current_user["id"]
    user_phase = current_user["phase"]

    # Check chat access
    access = await ChatAccessControl.can_access_chat(user_id, user_phase, db)
    if not access["can_access"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": access["reason"],
                "next_available": access.get("next_available"),
            },
        )

    meeting_id = access.get("meeting_id")

    # Save user message
    user_message_doc = MessageModel.create_message_document(
        user_id=user_id,
        role="user",
        content=content,
        meeting_id=meeting_id,
    )
    await db.chat_messages.insert_one(user_message_doc)

    # Get context
    user_goals = await get_user_goals(user_id, db)
    history = await get_conversation_history(user_id, db, limit=10, meeting_id=meeting_id)

    # Get the LLM service (uses DEFAULT_LLM_PROVIDER from config)
    try:
        llm_service = LLMServiceFactory.get_service()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )

    # Get response from LLM service
    response = await llm_service.send_message(
        message=content,
        conversation_history=history,
        user_phase=user_phase,
        user_goals=user_goals,
    )

    # Save assistant message
    assistant_message_doc = MessageModel.create_message_document(
        user_id=user_id,
        role="assistant",
        content=response["content"],
        meeting_id=meeting_id,
        model=response.get("model"),
        tokens_used=response.get("tokens_used"),
    )
    result = await db.chat_messages.insert_one(assistant_message_doc)

    return {
        "message_id": str(result.inserted_id),
        "content": response["content"],
        "tokens_used": response.get("tokens_used"),
        "model": response.get("model"),
    }
