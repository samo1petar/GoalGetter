"""
Pydantic schemas for Chat-related requests and responses.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class MessageMetadata(BaseModel):
    """Metadata for a chat message."""
    model: Optional[str] = None
    tokens_used: Optional[int] = None


class MessageBase(BaseModel):
    """Base message schema with common fields."""
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=10000)


class MessageCreate(BaseModel):
    """Schema for creating a new message (user sending a message)."""
    content: str = Field(..., min_length=1, max_length=10000)


class MessageResponse(MessageBase):
    """Schema for message response."""
    id: str
    user_id: str
    meeting_id: Optional[str] = None
    timestamp: str
    metadata: MessageMetadata

    class Config:
        from_attributes = True


class ChatHistoryResponse(BaseModel):
    """Schema for chat history response."""
    messages: List[MessageResponse]
    total: int
    page: int = 1
    page_size: int = 50
    has_more: bool = False


class ChatAccessResponse(BaseModel):
    """Schema for chat access check response."""
    can_access: bool
    reason: str
    user_phase: str
    next_available: Optional[str] = None  # ISO datetime string when chat becomes available
    meeting_id: Optional[str] = None  # Active meeting ID if in tracking phase


class WebSocketMessage(BaseModel):
    """Schema for WebSocket message from client."""
    type: str = Field(..., pattern="^(message|typing|ping)$")
    content: Optional[str] = None


class WebSocketResponse(BaseModel):
    """Schema for WebSocket response to client."""
    type: str  # "response", "response_chunk", "typing", "error", "connected", "pong"
    content: Optional[str] = None
    message_id: Optional[str] = None
    is_complete: bool = False
    error: Optional[str] = None


class StreamingChunk(BaseModel):
    """Schema for streaming response chunks."""
    type: str = "response_chunk"
    content: str
    message_id: str
    is_complete: bool = False


class ChatSessionInfo(BaseModel):
    """Schema for chat session information."""
    session_id: str
    user_id: str
    connected_at: str
    user_phase: str
    chat_enabled: bool


class ClearHistoryResponse(BaseModel):
    """Schema for clear history response."""
    success: bool
    deleted_count: int
    message: str
