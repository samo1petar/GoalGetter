"""
Claude AI service with Tony Robbins coaching persona.
Handles interactions with the Anthropic Claude API.
"""
import logging
from typing import Optional, List, Dict, Any, AsyncGenerator
from anthropic import Anthropic, AsyncAnthropic, APIError

from app.core.config import settings

logger = logging.getLogger(__name__)

# Tony Robbins System Prompt
TONY_ROBBINS_SYSTEM_PROMPT = """You are Tony Robbins, the world's #1 life and business strategist and peak performance coach.

YOUR MISSION: Help users set and achieve meaningful, transformative goals that align with their values and potential.

YOUR PERSONALITY:
- ENERGIZING: Use powerful, action-oriented language that ignites motivation
- COMPASSIONATE: Show deep empathy and understanding for their struggles
- DIRECT: Get straight to the point - no fluff, no beating around the bush
- GOAL-ORIENTED: Everything you say drives toward results and achievement
- REALISTIC: Challenge them to dream big while ensuring goals are achievable

YOUR APPROACH TO GOAL SETTING:
1. Ask powerful questions that reveal what they truly want
2. Help them clarify their "why" - the deep reason behind each goal
3. Ensure goals are SMART (Specific, Measurable, Achievable, Relevant, Time-bound)
4. Break down big goals into actionable steps
5. Identify potential obstacles and create strategies to overcome them
6. Celebrate their commitment and progress

COACHING GUIDELINES:
- Use phrases like: "Let me ask you something...", "Here's what I know...", "I challenge you to..."
- Reference their specific goals and progress in your responses
- If goals seem unrealistic, compassionately challenge them to refine
- Praise specific actions and commitments, not just intentions
- Keep responses concise but impactful (2-4 paragraphs)
- When appropriate, share brief analogies or stories to illustrate points

WHAT TO WATCH FOR:
- Goals that are too vague (help them get specific)
- Goals that are too easy (challenge them to level up)
- Goals that are unrealistic given their timeline (help them adjust)
- Multiple conflicting goals (help them prioritize)
- Goals without clear next actions (help them create action steps)

CURRENT CONTEXT:
User Phase: {user_phase}

Current Goals:
{user_goals}

Remember: Your job is to be their champion, their challenger, and their accountability partner. Push them to be their best while supporting them every step of the way."""


class ClaudeService:
    """
    Service for interacting with the Anthropic Claude API.
    Implements the Tony Robbins coaching persona.
    """

    def __init__(self):
        """Initialize the Claude service."""
        self.api_key = settings.ANTHROPIC_API_KEY
        self.model = settings.ANTHROPIC_MODEL
        self.max_tokens = settings.ANTHROPIC_MAX_TOKENS
        self.temperature = settings.ANTHROPIC_TEMPERATURE
        self._async_client: Optional[AsyncAnthropic] = None

    @property
    def is_configured(self) -> bool:
        """Check if the API key is configured."""
        return bool(self.api_key)

    def _get_async_client(self) -> AsyncAnthropic:
        """Get or create async Anthropic client."""
        if not self.is_configured:
            raise ValueError("ANTHROPIC_API_KEY is not configured")

        if self._async_client is None:
            self._async_client = AsyncAnthropic(api_key=self.api_key)

        return self._async_client

    def _build_system_prompt(
        self,
        user_phase: str = "goal_setting",
        user_goals: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Build the system prompt with user context injected.

        Args:
            user_phase: The user's current phase ("goal_setting" or "tracking")
            user_goals: List of user's goals with title and content

        Returns:
            Formatted system prompt string
        """
        # Format goals for context
        if user_goals:
            goals_text = "\n".join([
                f"- {goal.get('title', 'Untitled Goal')}: {goal.get('content', 'No content')[:200]}..."
                if len(goal.get('content', '')) > 200
                else f"- {goal.get('title', 'Untitled Goal')}: {goal.get('content', 'No content')}"
                for goal in user_goals[:5]  # Limit to 5 most recent goals
            ])
        else:
            goals_text = "No goals set yet."

        return TONY_ROBBINS_SYSTEM_PROMPT.format(
            user_phase=user_phase,
            user_goals=goals_text,
        )

    async def send_message(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_phase: str = "goal_setting",
        user_goals: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Send a message to Claude and get a response.

        Args:
            message: The user's message
            conversation_history: Previous messages in the conversation
            user_phase: The user's current phase
            user_goals: The user's current goals

        Returns:
            Dict with response content and metadata
        """
        if not self.is_configured:
            return {
                "content": "I apologize, but the AI coaching service is currently unavailable. The ANTHROPIC_API_KEY has not been configured. Please contact support to enable AI coaching.",
                "error": "API key not configured",
                "tokens_used": 0,
                "model": None,
            }

        try:
            client = self._get_async_client()

            # Build messages array
            messages = []
            if conversation_history:
                messages.extend(conversation_history)
            messages.append({"role": "user", "content": message})

            # Build system prompt with context
            system_prompt = self._build_system_prompt(user_phase, user_goals)

            # Call Claude API
            response = await client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=messages,
            )

            # Extract response
            content = response.content[0].text if response.content else ""
            tokens_used = response.usage.input_tokens + response.usage.output_tokens

            return {
                "content": content,
                "error": None,
                "tokens_used": tokens_used,
                "model": self.model,
            }

        except APIError as e:
            logger.error(f"Claude API error: {e}")
            return {
                "content": "I apologize, but I'm having trouble connecting right now. Please try again in a moment.",
                "error": str(e),
                "tokens_used": 0,
                "model": self.model,
            }
        except Exception as e:
            logger.error(f"Unexpected error in Claude service: {e}")
            return {
                "content": "An unexpected error occurred. Please try again.",
                "error": str(e),
                "tokens_used": 0,
                "model": self.model,
            }

    async def stream_message(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_phase: str = "goal_setting",
        user_goals: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream a message response from Claude.

        Args:
            message: The user's message
            conversation_history: Previous messages in the conversation
            user_phase: The user's current phase
            user_goals: The user's current goals

        Yields:
            Dict with chunk content and metadata
        """
        if not self.is_configured:
            yield {
                "type": "error",
                "content": "I apologize, but the AI coaching service is currently unavailable. The ANTHROPIC_API_KEY has not been configured. Please contact support to enable AI coaching.",
                "error": "API key not configured",
                "is_complete": True,
            }
            return

        try:
            client = self._get_async_client()

            # Build messages array
            messages = []
            if conversation_history:
                messages.extend(conversation_history)
            messages.append({"role": "user", "content": message})

            # Build system prompt with context
            system_prompt = self._build_system_prompt(user_phase, user_goals)

            # Stream from Claude API
            async with client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=messages,
            ) as stream:
                full_content = ""
                async for text in stream.text_stream:
                    full_content += text
                    yield {
                        "type": "chunk",
                        "content": text,
                        "is_complete": False,
                    }

                # Get final message for usage stats
                final_message = await stream.get_final_message()
                tokens_used = final_message.usage.input_tokens + final_message.usage.output_tokens

                yield {
                    "type": "complete",
                    "content": full_content,
                    "tokens_used": tokens_used,
                    "model": self.model,
                    "is_complete": True,
                }

        except APIError as e:
            logger.error(f"Claude API error during streaming: {e}")
            yield {
                "type": "error",
                "content": "I apologize, but I'm having trouble connecting right now. Please try again in a moment.",
                "error": str(e),
                "is_complete": True,
            }
        except Exception as e:
            logger.error(f"Unexpected error in Claude streaming: {e}")
            yield {
                "type": "error",
                "content": "An unexpected error occurred. Please try again.",
                "error": str(e),
                "is_complete": True,
            }

    async def close(self):
        """Close the async client."""
        if self._async_client:
            await self._async_client.close()
            self._async_client = None


# Global service instance
claude_service = ClaudeService()


async def get_claude_service() -> ClaudeService:
    """Dependency for getting Claude service in route handlers."""
    return claude_service
