"""
Context Service for Session Context Memory.
Handles context extraction, storage, and rolling summarization.
"""
import json
import logging
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from bson import ObjectId

from app.core.config import settings
from app.models.session_context import SessionContextModel
from app.services.llm import LLMServiceFactory

logger = logging.getLogger(__name__)

# Threshold for periodic context save during long sessions
MESSAGE_COUNT_THRESHOLD = 1000

# Threshold for rolling summarization
SUMMARIZATION_THRESHOLD = 20  # Summarize when >= 20 unsummarized sessions
SESSIONS_TO_SUMMARIZE = 10  # Summarize oldest 10 sessions


class ContextService:
    """
    Service for managing session context extraction and summarization.
    """

    def __init__(self, db):
        """Initialize the context service with a database connection."""
        self.db = db

    async def generate_session_id(self) -> str:
        """Generate a unique session ID."""
        return str(uuid.uuid4())

    async def get_conversation_history(
        self,
        user_id: str,
        limit: int = 100,
        since: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history for context extraction.

        Args:
            user_id: The user's ID
            limit: Maximum number of messages to retrieve
            since: Only get messages after this timestamp

        Returns:
            List of message dicts with role and content
        """
        query = {"user_id": ObjectId(user_id)}
        if since:
            query["timestamp"] = {"$gte": since}

        cursor = self.db.chat_messages.find(
            query,
            sort=[("timestamp", -1)],
            limit=limit,
        )
        messages = await cursor.to_list(length=limit)

        # Reverse to get chronological order
        messages = list(reversed(messages))

        return [
            {
                "role": msg["role"],
                "content": msg["content"],
                "timestamp": msg["timestamp"],
            }
            for msg in messages
        ]

    async def extract_session_context(
        self,
        user_id: str,
        session_id: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Use AI to extract meaningful context points from conversation.

        Args:
            user_id: The user's ID
            session_id: The session ID
            conversation_history: Messages to extract context from

        Returns:
            Extracted session context document or None if extraction fails
        """
        if not conversation_history or len(conversation_history) < 2:
            logger.info(f"Skipping context extraction - insufficient messages for user {user_id}")
            return None

        # Build conversation text for extraction
        conversation_text = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in conversation_history
        ])

        extraction_prompt = """Analyze this conversation between a user and their AI Coach and extract key points to remember for future sessions.

CONVERSATION:
{conversation}

Extract the following types of context points (only include what's actually present):

1. **goal_progress** - Goals created, updated, completed, milestones reached, deadlines set
2. **decision** - Key choices the user made about priorities, approaches, focus areas
3. **action_item** - Commitments user made, tasks they plan to do
4. **insight** - User preferences, working style, motivations discovered
5. **preference** - User's scheduling preferences, communication style, etc.
6. **blocker** - Challenges discussed, obstacles identified

Return a JSON object with the following structure:
{{
    "goals": [
        {{
            "goal_name": "Name of the goal discussed",
            "goal_id": "Goal ID if mentioned, otherwise null",
            "key_points": [
                {{
                    "type": "decision|discussion|progress|action_item|blocker",
                    "content": "Brief description of what was decided or discussed"
                }}
            ]
        }}
    ],
    "general_insights": [
        {{
            "type": "preference|insight",
            "content": "User preferences or insights not tied to a specific goal"
        }}
    ],
    "stats": {{
        "goals_created": <number>,
        "goals_updated": <number>,
        "goals_completed": <number>
    }}
}}

Be concise but capture essential information. Only include meaningful points - skip trivial greetings or small talk.
Include discussions even if no decision was made - they could be useful context for future sessions.
If there's nothing meaningful to extract, return {{"goals": [], "general_insights": [], "stats": {{"goals_created": 0, "goals_updated": 0, "goals_completed": 0}}}}
"""

        try:
            llm_service = LLMServiceFactory.get_service()

            # Build a simple prompt for extraction (no tools needed)
            response = await llm_service.send_message(
                message=extraction_prompt.format(conversation=conversation_text[:15000]),  # Limit context
                conversation_history=None,
                user_phase="goal_setting",
                user_goals=None,
                draft_goals=None,
            )

            content = response.get("content", "")

            # Parse JSON response
            # Try to extract JSON from the response
            json_start = content.find("{")
            json_end = content.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                extracted = json.loads(json_str)

                # Build context points from goal-based structure
                context_points = []

                # Process goal-specific points
                for goal in extracted.get("goals", []):
                    goal_name = goal.get("goal_name", "Unknown goal")
                    goal_id = goal.get("goal_id")

                    for point in goal.get("key_points", []):
                        point_type = point.get("type", "discussion")
                        if point_type in SessionContextModel.VALID_CONTEXT_TYPES:
                            context_points.append(
                                SessionContextModel.create_context_point(
                                    type=point_type,
                                    content=f"[{goal_name}] {point.get('content', '')}",
                                    related_goal_id=goal_id,
                                )
                            )

                # Process general insights
                for insight in extracted.get("general_insights", []):
                    if insight.get("type") in SessionContextModel.VALID_CONTEXT_TYPES:
                        context_points.append(
                            SessionContextModel.create_context_point(
                                type=insight["type"],
                                content=insight.get("content", ""),
                            )
                        )

                # Get stats
                stats = extracted.get("stats", {})

                # Create session context document
                session_context = SessionContextModel.create_session_context_document(
                    user_id=user_id,
                    session_id=session_id,
                    context_points=context_points,
                    message_count=len(conversation_history),
                    goals_created=stats.get("goals_created", 0),
                    goals_updated=stats.get("goals_updated", 0),
                    goals_completed=stats.get("goals_completed", 0),
                )
                session_context["ended_at"] = datetime.utcnow()

                return session_context

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse context extraction JSON: {e}")
        except Exception as e:
            logger.error(f"Error extracting session context: {e}")

        return None

    async def save_session_context(
        self,
        session_context: Dict[str, Any],
    ) -> Optional[str]:
        """
        Save a session context to the database.

        Args:
            session_context: The session context document to save

        Returns:
            The inserted document ID or None if save fails
        """
        try:
            result = await self.db.session_contexts.insert_one(session_context)
            logger.info(f"Saved session context {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Failed to save session context: {e}")
            return None

    async def extract_and_save_context(
        self,
        user_id: str,
        session_id: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Optional[str]:
        """
        Extract context from conversation and save it.
        This is the main entry point for context extraction.

        Args:
            user_id: The user's ID
            session_id: The session ID
            conversation_history: Messages to extract from (fetched if not provided)

        Returns:
            The saved context ID or None if extraction/save fails
        """
        try:
            # Fetch conversation if not provided
            if conversation_history is None:
                conversation_history = await self.get_conversation_history(user_id)

            if not conversation_history or len(conversation_history) < 2:
                logger.info(f"No meaningful conversation to extract for user {user_id}")
                return None

            # Extract context
            session_context = await self.extract_session_context(
                user_id=user_id,
                session_id=session_id,
                conversation_history=conversation_history,
            )

            if not session_context or not session_context.get("context_points"):
                logger.info(f"No context points extracted for user {user_id}")
                return None

            # Save context
            context_id = await self.save_session_context(session_context)

            # Check if rolling summarization is needed
            if context_id:
                await self.maybe_summarize_old_sessions(user_id)

            return context_id

        except Exception as e:
            logger.error(f"Error in extract_and_save_context: {e}")
            return None

    async def get_unsummarized_sessions(
        self,
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Get all unsummarized session contexts for a user.

        Args:
            user_id: The user's ID

        Returns:
            List of unsummarized session context documents
        """
        cursor = self.db.session_contexts.find(
            {
                "user_id": ObjectId(user_id),
                "is_summary": False,
            },
            sort=[("created_at", 1)],
        )
        return await cursor.to_list(length=100)

    async def maybe_summarize_old_sessions(
        self,
        user_id: str,
    ) -> Optional[str]:
        """
        Check if summarization is needed and perform it.

        Rule: After every 10 new unsummarized sessions beyond 10,
        summarize the oldest 10 unsummarized sessions.

        Args:
            user_id: The user's ID

        Returns:
            The summary context ID if created, None otherwise
        """
        try:
            unsummarized = await self.get_unsummarized_sessions(user_id)

            if len(unsummarized) < SUMMARIZATION_THRESHOLD:
                return None

            logger.info(f"User {user_id} has {len(unsummarized)} unsummarized sessions, triggering summarization")

            # Get oldest 10 unsummarized sessions
            to_summarize = unsummarized[:SESSIONS_TO_SUMMARIZE]

            # Create summary
            summary = await self.create_session_summary(user_id, to_summarize)

            if summary:
                # Save summary
                summary_id = await self.save_session_context(summary)

                # Mark original sessions as summarized (delete them)
                session_ids = [ctx["_id"] for ctx in to_summarize]
                await self.db.session_contexts.delete_many({"_id": {"$in": session_ids}})

                logger.info(f"Created summary {summary_id} from {len(to_summarize)} sessions")
                return summary_id

        except Exception as e:
            logger.error(f"Error in summarization: {e}")

        return None

    async def create_session_summary(
        self,
        user_id: str,
        sessions: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        Combine multiple session contexts into a single summary.

        Args:
            user_id: The user's ID
            sessions: List of session context documents to summarize

        Returns:
            Summary session context document or None if summarization fails
        """
        if not sessions:
            return None

        # Build context text from all sessions
        context_text_parts = []
        total_message_count = 0
        total_goals_created = 0
        total_goals_updated = 0
        total_goals_completed = 0

        for session in sessions:
            total_message_count += session.get("message_count", 0)
            total_goals_created += session.get("goals_created", 0)
            total_goals_updated += session.get("goals_updated", 0)
            total_goals_completed += session.get("goals_completed", 0)

            for point in session.get("context_points", []):
                context_text_parts.append(f"- [{point['type']}] {point['content']}")

        if not context_text_parts:
            return None

        date_range_start = sessions[0].get("created_at", datetime.utcnow())
        date_range_end = sessions[-1].get("ended_at") or sessions[-1].get("created_at", datetime.utcnow())

        summarization_prompt = f"""Summarize these {len(sessions)} session context points into a concise summary.
Date range: {date_range_start.strftime('%Y-%m-%d')} to {date_range_end.strftime('%Y-%m-%d')}

CONTEXT POINTS:
{chr(10).join(context_text_parts)}

Combine similar points, remove redundancy, keep the most important:
- Major goal achievements
- Significant decisions
- Ongoing action items (not completed ones)
- Key user preferences discovered
- Important blockers or challenges

Return a JSON object:
{{
    "context_points": [
        {{
            "type": "goal_progress|decision|action_item|insight|preference|blocker",
            "content": "Summarized context point"
        }}
    ]
}}

Be concise but comprehensive. Aim for 5-15 key points maximum."""

        try:
            llm_service = LLMServiceFactory.get_service()

            response = await llm_service.send_message(
                message=summarization_prompt,
                conversation_history=None,
                user_phase="goal_setting",
                user_goals=None,
                draft_goals=None,
            )

            content = response.get("content", "")

            # Parse JSON response
            json_start = content.find("{")
            json_end = content.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                extracted = json.loads(json_str)

                # Create context points
                context_points = []
                for point in extracted.get("context_points", []):
                    if point.get("type") in SessionContextModel.VALID_CONTEXT_TYPES:
                        context_points.append(
                            SessionContextModel.create_context_point(
                                type=point["type"],
                                content=point.get("content", ""),
                                timestamp=date_range_end,
                            )
                        )

                # Create summary document
                summary = SessionContextModel.create_session_context_document(
                    user_id=user_id,
                    session_id=f"summary-{uuid.uuid4()}",
                    context_points=context_points,
                    message_count=total_message_count,
                    goals_created=total_goals_created,
                    goals_updated=total_goals_updated,
                    goals_completed=total_goals_completed,
                    is_summary=True,
                    summarized_session_ids=[ctx["session_id"] for ctx in sessions],
                )
                summary["created_at"] = date_range_start
                summary["ended_at"] = date_range_end

                return summary

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse summarization JSON: {e}")
        except Exception as e:
            logger.error(f"Error creating session summary: {e}")

        return None

    async def load_user_context(
        self,
        user_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Load all relevant context for a user (summaries + recent sessions).

        Args:
            user_id: The user's ID
            limit: Maximum number of recent sessions to include

        Returns:
            List of session context documents (summaries + recent)
        """
        # Get all summaries
        summaries_cursor = self.db.session_contexts.find(
            {
                "user_id": ObjectId(user_id),
                "is_summary": True,
            },
            sort=[("created_at", 1)],
        )
        summaries = await summaries_cursor.to_list(length=100)

        # Get recent unsummarized sessions
        recent_cursor = self.db.session_contexts.find(
            {
                "user_id": ObjectId(user_id),
                "is_summary": False,
            },
            sort=[("created_at", -1)],
            limit=limit,
        )
        recent = await recent_cursor.to_list(length=limit)

        # Combine: summaries (chronological) + recent (reverse for chronological)
        return summaries + list(reversed(recent))

    async def get_context_history(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """
        Get paginated context history for a user.

        Args:
            user_id: The user's ID
            page: Page number (1-indexed)
            page_size: Number of contexts per page

        Returns:
            Dict with contexts, total, page, page_size, has_more
        """
        skip = (page - 1) * page_size

        # Get total count
        total = await self.db.session_contexts.count_documents({
            "user_id": ObjectId(user_id),
        })

        # Get paginated contexts
        cursor = self.db.session_contexts.find(
            {"user_id": ObjectId(user_id)},
            sort=[("created_at", -1)],
            skip=skip,
            limit=page_size,
        )
        contexts = await cursor.to_list(length=page_size)

        return {
            "contexts": SessionContextModel.serialize_session_contexts(contexts),
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": (skip + len(contexts)) < total,
        }

    async def delete_user_context(
        self,
        user_id: str,
    ) -> int:
        """
        Delete all context data for a user (GDPR compliance).

        Args:
            user_id: The user's ID

        Returns:
            Number of documents deleted
        """
        result = await self.db.session_contexts.delete_many({
            "user_id": ObjectId(user_id),
        })
        logger.info(f"Deleted {result.deleted_count} context documents for user {user_id}")
        return result.deleted_count


    async def is_first_time_user(self, user_id: str) -> bool:
        """
        Check if user has any prior context or chat history.

        A first-time user is defined as someone with:
        - No session context records
        - No chat messages

        Args:
            user_id: The user's ID

        Returns:
            True if first-time user, False otherwise
        """
        try:
            # Check for session contexts
            context_count = await self.db.session_contexts.count_documents({
                "user_id": ObjectId(user_id),
            })

            if context_count > 0:
                return False

            # Check for chat messages
            message_count = await self.db.chat_messages.count_documents({
                "user_id": ObjectId(user_id),
            })

            return message_count == 0

        except Exception as e:
            logger.error(f"Error checking first-time user status: {e}")
            # Default to False (treat as returning user) on error
            return False


# Factory function for getting service instance
def get_context_service(db) -> ContextService:
    """Get a context service instance."""
    return ContextService(db)
