"""
Chat message model for MongoDB.
Represents chat messages between users and the AI coach.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from bson import ObjectId


class MessageModel:
    """
    Message model representing a chat message document in the database.
    This is a dict-based model for MongoDB documents.
    """

    VALID_ROLES = ["user", "assistant"]

    @staticmethod
    def create_message_document(
        user_id: str,
        role: str,
        content: str,
        meeting_id: Optional[str] = None,
        model: Optional[str] = None,
        tokens_used: Optional[int] = None,
    ) -> dict:
        """Create a new chat message document for MongoDB."""
        if role not in MessageModel.VALID_ROLES:
            raise ValueError(f"Invalid role: {role}. Must be one of {MessageModel.VALID_ROLES}")

        return {
            "user_id": ObjectId(user_id),
            "meeting_id": ObjectId(meeting_id) if meeting_id else None,
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow(),
            "metadata": {
                "model": model,
                "tokens_used": tokens_used,
            }
        }

    @staticmethod
    def serialize_message(message_doc: dict) -> Optional[dict]:
        """Serialize message document for API response."""
        if not message_doc:
            return None

        return {
            "id": str(message_doc["_id"]),
            "user_id": str(message_doc["user_id"]),
            "meeting_id": str(message_doc["meeting_id"]) if message_doc.get("meeting_id") else None,
            "role": message_doc["role"],
            "content": message_doc["content"],
            "timestamp": message_doc["timestamp"].isoformat() if isinstance(message_doc["timestamp"], datetime) else message_doc["timestamp"],
            "metadata": {
                "model": message_doc.get("metadata", {}).get("model"),
                "tokens_used": message_doc.get("metadata", {}).get("tokens_used"),
            }
        }

    @staticmethod
    def serialize_messages(messages: List[dict]) -> List[dict]:
        """Serialize multiple message documents for API response."""
        return [MessageModel.serialize_message(msg) for msg in messages if msg]

    @staticmethod
    def to_chat_history_format(messages: List[dict]) -> List[dict]:
        """
        Convert messages to the format expected by Claude API.
        Returns list of {"role": "user"|"assistant", "content": "..."} dicts.
        """
        return [
            {
                "role": msg["role"],
                "content": msg["content"]
            }
            for msg in messages
            if msg.get("role") in MessageModel.VALID_ROLES
        ]
