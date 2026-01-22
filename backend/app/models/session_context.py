"""
Session Context model for MongoDB.
Represents session context data for AI Coach memory across sessions.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from bson import ObjectId


class SessionContextModel:
    """
    Session Context model representing context extracted from a chat session.
    This is a dict-based model for MongoDB documents.
    """

    VALID_CONTEXT_TYPES = [
        "goal_progress",
        "decision",
        "discussion",
        "progress",
        "action_item",
        "insight",
        "preference",
        "blocker",
    ]

    @staticmethod
    def create_context_point(
        type: str,
        content: str,
        related_goal_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> dict:
        """Create a context point document."""
        if type not in SessionContextModel.VALID_CONTEXT_TYPES:
            raise ValueError(
                f"Invalid context type: {type}. Must be one of {SessionContextModel.VALID_CONTEXT_TYPES}"
            )

        return {
            "type": type,
            "content": content,
            "related_goal_id": ObjectId(related_goal_id) if related_goal_id else None,
            "timestamp": timestamp or datetime.utcnow(),
        }

    @staticmethod
    def create_session_context_document(
        user_id: str,
        session_id: str,
        context_points: Optional[List[Dict[str, Any]]] = None,
        message_count: int = 0,
        goals_created: int = 0,
        goals_updated: int = 0,
        goals_completed: int = 0,
        is_summary: bool = False,
        summarized_session_ids: Optional[List[str]] = None,
    ) -> dict:
        """Create a new session context document for MongoDB."""
        return {
            "user_id": ObjectId(user_id),
            "session_id": session_id,
            "created_at": datetime.utcnow(),
            "ended_at": None,
            "context_points": context_points or [],
            "message_count": message_count,
            "goals_created": goals_created,
            "goals_updated": goals_updated,
            "goals_completed": goals_completed,
            "is_summary": is_summary,
            "summarized_session_ids": summarized_session_ids,
        }

    @staticmethod
    def serialize_context_point(point: dict) -> Optional[dict]:
        """Serialize a context point for API response."""
        if not point:
            return None

        return {
            "type": point["type"],
            "content": point["content"],
            "related_goal_id": str(point["related_goal_id"]) if point.get("related_goal_id") else None,
            "timestamp": (
                point["timestamp"].isoformat()
                if isinstance(point["timestamp"], datetime)
                else point["timestamp"]
            ),
        }

    @staticmethod
    def serialize_session_context(context_doc: dict) -> Optional[dict]:
        """Serialize session context document for API response."""
        if not context_doc:
            return None

        return {
            "id": str(context_doc["_id"]),
            "user_id": str(context_doc["user_id"]),
            "session_id": context_doc["session_id"],
            "created_at": (
                context_doc["created_at"].isoformat()
                if isinstance(context_doc["created_at"], datetime)
                else context_doc["created_at"]
            ),
            "ended_at": (
                context_doc["ended_at"].isoformat()
                if isinstance(context_doc.get("ended_at"), datetime)
                else context_doc.get("ended_at")
            ),
            "context_points": [
                SessionContextModel.serialize_context_point(point)
                for point in context_doc.get("context_points", [])
            ],
            "message_count": context_doc.get("message_count", 0),
            "goals_created": context_doc.get("goals_created", 0),
            "goals_updated": context_doc.get("goals_updated", 0),
            "goals_completed": context_doc.get("goals_completed", 0),
            "is_summary": context_doc.get("is_summary", False),
            "summarized_session_ids": context_doc.get("summarized_session_ids"),
        }

    @staticmethod
    def serialize_session_contexts(contexts: List[dict]) -> List[dict]:
        """Serialize multiple session context documents for API response."""
        return [
            SessionContextModel.serialize_session_context(ctx)
            for ctx in contexts
            if ctx
        ]

    @staticmethod
    def to_context_summary_format(contexts: List[dict]) -> str:
        """
        Convert session contexts to a summary format for AI prompt injection.
        Returns a formatted string with context points organized by type.
        """
        if not contexts:
            return "No previous session context available."

        organized = {
            "goal_progress": [],
            "progress": [],
            "decision": [],
            "discussion": [],
            "action_item": [],
            "insight": [],
            "preference": [],
            "blocker": [],
        }

        for ctx in contexts:
            for point in ctx.get("context_points", []):
                point_type = point.get("type")
                if point_type in organized:
                    organized[point_type].append(point.get("content", ""))

        summary_parts = []

        # Combine goal_progress and progress
        all_progress = organized["goal_progress"] + organized["progress"]
        if all_progress:
            summary_parts.append("**Goal Progress:**")
            for item in all_progress[-10:]:  # Last 10 items
                summary_parts.append(f"- {item}")

        if organized["decision"]:
            summary_parts.append("\n**Key Decisions:**")
            for item in organized["decision"][-5:]:
                summary_parts.append(f"- {item}")

        if organized["discussion"]:
            summary_parts.append("\n**Discussions:**")
            for item in organized["discussion"][-5:]:
                summary_parts.append(f"- {item}")

        if organized["action_item"]:
            summary_parts.append("\n**Action Items:**")
            for item in organized["action_item"][-5:]:
                summary_parts.append(f"- {item}")

        if organized["insight"]:
            summary_parts.append("\n**Insights:**")
            for item in organized["insight"][-5:]:
                summary_parts.append(f"- {item}")

        if organized["preference"]:
            summary_parts.append("\n**User Preferences:**")
            for item in organized["preference"][-5:]:
                summary_parts.append(f"- {item}")

        if organized["blocker"]:
            summary_parts.append("\n**Blockers/Challenges:**")
            for item in organized["blocker"][-3:]:
                summary_parts.append(f"- {item}")

        return "\n".join(summary_parts) if summary_parts else "No meaningful context points available."
