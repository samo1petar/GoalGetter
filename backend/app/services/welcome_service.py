"""
Welcome Service for Session Context Memory.
Handles welcome message generation for both first-time and returning users.

On each login, users see a fresh chat with a personalized welcome:
- First-time users: Get an onboarding guide explaining the tool
- Returning users: Get a progress summary based on prior sessions and active goals
"""
import logging
from typing import Optional, List, Dict, Any
from bson import ObjectId

from app.models.session_context import SessionContextModel
from app.models.goal import GoalModel
from app.services.context_service import ContextService
from app.services.llm import LLMServiceFactory

logger = logging.getLogger(__name__)

# Onboarding message for first-time users
FIRST_TIME_USER_WELCOME = """Welcome to GoalGetter!

I'm Alfred, your AI Coach. I'm here to help you set, track, and achieve your goals. Here's how we can work together:

**Set Goals** - Tell me what you want to achieve and I'll help you create structured, actionable goals with clear milestones and deadlines.

**Track Progress** - Share your updates and I'll help you stay accountable and motivated. We'll celebrate wins and work through challenges together.

**Get Guidance** - Ask me for advice, strategies, or help breaking down complex goals into manageable steps.

Ready to get started? Tell me about a goal you'd like to work on, or ask me anything!"""


class WelcomeService:
    """
    Service for generating personalized welcome summaries for returning users.
    """

    def __init__(self, db):
        """Initialize the welcome service with a database connection."""
        self.db = db
        self.context_service = ContextService(db)

    async def get_user_goals(
        self,
        user_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get user's current goals for context in welcome summary.

        Args:
            user_id: The user's ID
            limit: Maximum number of goals to retrieve

        Returns:
            List of serialized goal documents
        """
        cursor = self.db.goals.find(
            {
                "user_id": ObjectId(user_id),
                "phase": {"$ne": "archived"},
            },
            sort=[("updated_at", -1)],
            limit=limit,
        )
        goals = await cursor.to_list(length=limit)
        return [GoalModel.serialize_goal(g) for g in goals]

    async def generate_welcome_summary(
        self,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate AI Coach's opening summary message for a returning user.

        Args:
            user_id: The user's ID

        Returns:
            Dict with 'summary' (the welcome message) and 'has_context' (bool)
            Returns None only if there's an error
        """
        try:
            # Load user context
            contexts = await self.context_service.load_user_context(user_id)

            # First-time user case
            if not contexts:
                return {
                    "summary": None,
                    "has_context": False,
                    "context_points_count": 0,
                    "sessions_count": 0,
                }

            # Get current goals for reference
            current_goals = await self.get_user_goals(user_id)

            # Format context for prompt
            context_summary = SessionContextModel.to_context_summary_format(contexts)

            # Format goals for prompt
            goals_text = ""
            if current_goals:
                goals_text = "\n".join([
                    f"- {goal['title']} ({goal['phase']})"
                    for goal in current_goals[:5]
                ])
            else:
                goals_text = "No active goals"

            # Calculate stats
            total_context_points = sum(
                len(ctx.get("context_points", []))
                for ctx in contexts
            )

            summary_prompt = f"""You are Alfred, the AI Coach. Generate a brief, warm welcome message summarizing the user's progress.

PREVIOUS SESSION CONTEXT:
{context_summary}

CURRENT GOALS:
{goals_text}

Generate a welcome message that:
1. Acknowledges their return warmly
2. Briefly mentions what they worked on recently (1-2 highlights)
3. References any pending action items or next steps
4. Encourages them to continue

IMPORTANT GUIDELINES:
- Keep it to 2-3 sentences maximum
- Be conversational and supportive
- Don't overwhelm them - just the highlights
- If they completed something, celebrate it briefly
- End with a forward-looking question or suggestion
- DO NOT include any JSON or structured data - just the natural message text

Example tone: "Welcome back! Last session you made great progress on your 'Learn TypeScript' goal - you completed 2 milestones and set a deadline for next month. Ready to tackle the next steps?"
"""

            llm_service = LLMServiceFactory.get_service()

            response = await llm_service.send_message(
                message=summary_prompt,
                conversation_history=None,
                user_phase="goal_setting",
                user_goals=None,
                draft_goals=None,
            )

            summary = response.get("content", "").strip()

            # Validate the summary is not empty and not JSON
            if not summary or summary.startswith("{"):
                logger.warning("Generated summary was invalid, using fallback")
                summary = self._generate_fallback_summary(contexts, current_goals)

            return {
                "summary": summary,
                "has_context": True,
                "context_points_count": total_context_points,
                "sessions_count": len(contexts),
            }

        except Exception as e:
            logger.error(f"Error generating welcome summary: {e}")
            return {
                "summary": None,
                "has_context": False,
                "context_points_count": 0,
                "sessions_count": 0,
                "error": str(e),
            }

    def _generate_fallback_summary(
        self,
        contexts: List[Dict[str, Any]],
        current_goals: List[Dict[str, Any]],
    ) -> str:
        """
        Generate a fallback summary when AI generation fails.

        Args:
            contexts: User's session contexts
            current_goals: User's current goals

        Returns:
            A basic welcome message
        """
        # Find the most recent meaningful context point
        recent_progress = None
        for ctx in reversed(contexts):
            for point in reversed(ctx.get("context_points", [])):
                if point.get("type") == "goal_progress":
                    recent_progress = point.get("content")
                    break
            if recent_progress:
                break

        if recent_progress and current_goals:
            return f"Welcome back! Last time we worked on your goals together. {recent_progress[:100]}... Ready to continue making progress?"
        elif current_goals:
            goal_titles = ", ".join([g["title"] for g in current_goals[:2]])
            return f"Welcome back! You have active goals including: {goal_titles}. What would you like to focus on today?"
        else:
            return "Welcome back! Ready to set some goals and make progress together?"

    async def check_is_first_time_user(
        self,
        user_id: str,
    ) -> bool:
        """
        Check if this is a first-time user (no previous session context or chat history).

        Args:
            user_id: The user's ID

        Returns:
            True if first-time user, False otherwise
        """
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

    async def generate_welcome_message(
        self,
        user_id: str,
        is_login: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate the welcome message for a user on login.

        This is the main entry point for generating welcome messages.
        - First-time users get an onboarding guide
        - Returning users get a personalized progress summary

        Args:
            user_id: The user's ID
            is_login: Whether this is an explicit login event. If False,
                      returns empty response (no welcome message).

        Returns:
            Dict with:
            - message: The welcome message content
            - is_first_time: Whether this is a first-time user
            - has_context: Whether the user has prior context
            - active_goals: List of active goals (for returning users)
        """
        # Only generate welcome message on explicit login
        if not is_login:
            return {
                "message": None,
                "is_first_time": False,
                "has_context": False,
                "active_goals": [],
            }

        try:
            # Check if first-time user
            is_first_time = await self.check_is_first_time_user(user_id)

            if is_first_time:
                return {
                    "message": FIRST_TIME_USER_WELCOME,
                    "is_first_time": True,
                    "has_context": False,
                    "active_goals": [],
                }

            # Returning user - generate personalized summary
            return await self._generate_returning_user_welcome(user_id)

        except Exception as e:
            logger.error(f"Error generating welcome message: {e}")
            # Fallback to first-time user experience on error
            return {
                "message": FIRST_TIME_USER_WELCOME,
                "is_first_time": True,
                "has_context": False,
                "active_goals": [],
                "error": str(e),
            }

    async def generate_returning_user_summary(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Generate a personalized summary for a returning user.

        This is called asynchronously after the quick welcome is sent.
        Skips the first-time user check since caller already verified.

        Args:
            user_id: The user's ID

        Returns:
            Dict with 'message' containing the AI-generated summary
        """
        return await self._generate_returning_user_welcome(user_id)

    async def _generate_returning_user_welcome(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Generate a personalized welcome message for a returning user.

        Includes:
        - Welcome back greeting
        - Progress summary from session contexts
        - Active goals with status
        - Pending action items
        - Conversation opener

        Args:
            user_id: The user's ID

        Returns:
            Dict with message content and metadata
        """
        # Load user context
        contexts = await self.context_service.load_user_context(user_id)

        # Get current goals
        current_goals = await self.get_user_goals(user_id)

        # Serialize goals for response
        active_goals = [
            {
                "id": goal["id"],
                "title": goal["title"],
                "phase": goal["phase"],
                "progress": self._calculate_goal_progress(goal),
            }
            for goal in current_goals
        ]

        # If no contexts but has goals, generate a goal-focused welcome
        if not contexts:
            message = self._generate_goal_focused_welcome(current_goals)
            return {
                "message": message,
                "is_first_time": False,
                "has_context": False,
                "active_goals": active_goals,
            }

        # Format context for prompt
        context_summary = SessionContextModel.to_context_summary_format(contexts)

        # Format goals for prompt
        goals_text = ""
        if current_goals:
            goals_parts = []
            for goal in current_goals[:5]:
                progress = self._calculate_goal_progress(goal)
                progress_str = f"{progress}% complete" if progress > 0 else goal["phase"]
                goals_parts.append(f"- {goal['title']} ({progress_str})")
            goals_text = "\n".join(goals_parts)
        else:
            goals_text = "No active goals"

        # Extract pending action items from contexts
        action_items = self._extract_action_items(contexts)
        action_items_text = "\n".join([f"- {item}" for item in action_items[:3]]) if action_items else "None"

        # Generate welcome using AI
        summary_prompt = f"""You are Alfred, the AI Coach. Generate a personalized welcome message for a returning user.

PREVIOUS SESSION CONTEXT:
{context_summary}

CURRENT GOALS:
{goals_text}

PENDING ACTION ITEMS:
{action_items_text}

Generate a welcome message that:
1. Warmly welcomes them back
2. Briefly summarizes their recent progress (1-2 key highlights from the context)
3. Lists their active goals with status
4. Mentions any pending action items they committed to
5. Ends with an engaging question about what they'd like to focus on today

FORMAT GUIDELINES:
- Use markdown formatting
- Keep it concise but informative (2-4 paragraphs max)
- Use **bold** for emphasis on goal names and key points
- Use bullet points for lists
- Be encouraging and supportive
- DO NOT include JSON or structured data - just natural conversational text

Example structure:
"Welcome back! [brief progress highlight]

**Your Goals:**
- [Goal 1] (status)
- [Goal 2] (status)

[Mention pending action items if any]

What would you like to focus on today?"
"""

        try:
            llm_service = LLMServiceFactory.get_service()

            response = await llm_service.send_message(
                message=summary_prompt,
                conversation_history=None,
                user_phase="goal_setting",
                user_goals=None,
                draft_goals=None,
            )

            message = response.get("content", "").strip()

            # Validate the message is not empty and not JSON
            if not message or message.startswith("{"):
                logger.warning("Generated welcome was invalid, using fallback")
                message = self._generate_fallback_welcome(contexts, current_goals, action_items)

            return {
                "message": message,
                "is_first_time": False,
                "has_context": True,
                "active_goals": active_goals,
            }

        except Exception as e:
            logger.error(f"Error generating AI welcome: {e}")
            message = self._generate_fallback_welcome(contexts, current_goals, action_items)
            return {
                "message": message,
                "is_first_time": False,
                "has_context": True,
                "active_goals": active_goals,
                "error": str(e),
            }

    def _calculate_goal_progress(self, goal: Dict[str, Any]) -> int:
        """
        Calculate completion percentage for a goal based on milestones.

        Args:
            goal: Serialized goal dict

        Returns:
            Progress percentage (0-100)
        """
        metadata = goal.get("metadata", {})
        milestones = metadata.get("milestones", [])

        if not milestones:
            # No milestones - use phase-based estimation
            phase = goal.get("phase", "draft")
            if phase == "completed":
                return 100
            elif phase == "active":
                return 10
            return 0

        completed = sum(1 for m in milestones if m.get("completed", False))
        return int((completed / len(milestones)) * 100)

    def _extract_action_items(self, contexts: List[Dict[str, Any]]) -> List[str]:
        """
        Extract pending action items from session contexts.

        Args:
            contexts: List of session context documents

        Returns:
            List of action item strings
        """
        action_items = []
        for ctx in reversed(contexts):  # Most recent first
            for point in ctx.get("context_points", []):
                if point.get("type") == "action_item":
                    content = point.get("content", "")
                    if content and content not in action_items:
                        action_items.append(content)
        return action_items[:5]  # Limit to 5 most recent

    def _generate_goal_focused_welcome(self, goals: List[Dict[str, Any]]) -> str:
        """
        Generate a welcome message focused on goals when no context exists.

        Args:
            goals: User's current goals

        Returns:
            Welcome message string
        """
        if not goals:
            return "Welcome back! Ready to set some goals and make progress together? Tell me what you'd like to achieve."

        goal_parts = []
        for goal in goals[:3]:
            progress = self._calculate_goal_progress(goal)
            if progress > 0:
                goal_parts.append(f"- **{goal['title']}** ({progress}% complete)")
            else:
                goal_parts.append(f"- **{goal['title']}** ({goal['phase']})")

        goals_text = "\n".join(goal_parts)

        return f"""Welcome back! Here are your active goals:

{goals_text}

What would you like to focus on today?"""

    def _generate_fallback_welcome(
        self,
        contexts: List[Dict[str, Any]],
        goals: List[Dict[str, Any]],
        action_items: List[str],
    ) -> str:
        """
        Generate a fallback welcome message when AI generation fails.

        Args:
            contexts: User's session contexts
            goals: User's current goals
            action_items: Pending action items

        Returns:
            Fallback welcome message
        """
        parts = ["Welcome back!"]

        # Find recent progress highlight
        recent_progress = None
        for ctx in reversed(contexts):
            for point in reversed(ctx.get("context_points", [])):
                if point.get("type") == "goal_progress":
                    recent_progress = point.get("content", "")[:100]
                    break
            if recent_progress:
                break

        if recent_progress:
            parts.append(f"Last session: {recent_progress}")

        # Add goals section
        if goals:
            parts.append("\n**Your Active Goals:**")
            for goal in goals[:3]:
                progress = self._calculate_goal_progress(goal)
                if progress > 0:
                    parts.append(f"- {goal['title']} ({progress}% complete)")
                else:
                    parts.append(f"- {goal['title']} ({goal['phase']})")

        # Add action items if any
        if action_items:
            parts.append("\n**Pending Items:**")
            for item in action_items[:2]:
                parts.append(f"- {item[:80]}")

        parts.append("\nWhat would you like to focus on today?")

        return "\n".join(parts)

    async def get_quick_context_summary(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Get a quick summary of user's context without AI generation.
        Useful for displaying context stats in the UI.

        Args:
            user_id: The user's ID

        Returns:
            Dict with context statistics
        """
        # Count total sessions
        total_sessions = await self.db.session_contexts.count_documents({
            "user_id": ObjectId(user_id),
            "is_summary": False,
        })

        # Count summaries
        total_summaries = await self.db.session_contexts.count_documents({
            "user_id": ObjectId(user_id),
            "is_summary": True,
        })

        # Get stats from sessions
        pipeline = [
            {"$match": {"user_id": ObjectId(user_id)}},
            {
                "$group": {
                    "_id": None,
                    "total_messages": {"$sum": "$message_count"},
                    "total_goals_created": {"$sum": "$goals_created"},
                    "total_goals_updated": {"$sum": "$goals_updated"},
                    "total_goals_completed": {"$sum": "$goals_completed"},
                    "total_context_points": {
                        "$sum": {"$size": {"$ifNull": ["$context_points", []]}}
                    },
                }
            },
        ]

        result = await self.db.session_contexts.aggregate(pipeline).to_list(length=1)

        stats = result[0] if result else {
            "total_messages": 0,
            "total_goals_created": 0,
            "total_goals_updated": 0,
            "total_goals_completed": 0,
            "total_context_points": 0,
        }

        return {
            "total_sessions": total_sessions,
            "total_summaries": total_summaries,
            "total_messages_processed": stats.get("total_messages", 0),
            "total_goals_created": stats.get("total_goals_created", 0),
            "total_goals_updated": stats.get("total_goals_updated", 0),
            "total_goals_completed": stats.get("total_goals_completed", 0),
            "total_context_points": stats.get("total_context_points", 0),
            "is_first_time": total_sessions == 0 and total_summaries == 0,
        }


# Factory function for getting service instance
def get_welcome_service(db) -> WelcomeService:
    """Get a welcome service instance."""
    return WelcomeService(db)
