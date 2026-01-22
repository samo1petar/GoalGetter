"""
Claude AI service with Tony Robbins coaching persona.
Handles interactions with the Anthropic Claude API.
Implements BaseLLMService interface for provider abstraction.
"""
import json
import logging
import anthropic
from typing import Optional, List, Dict, Any, AsyncGenerator
from anthropic import AsyncAnthropic, APIError

from app.core.config import settings
from .base import BaseLLMService

logger = logging.getLogger(__name__)

# Enable Anthropic SDK debug logging - logs all API traffic
anthropic.log = "debug"


def log_claude_request(system_prompt: str, messages: List[Dict], model: str, max_tokens: int, temperature: float):
    """Log the full request being sent to Claude API."""
    logger.info("=" * 80)
    logger.info("CLAUDE API REQUEST")
    logger.info("=" * 80)
    logger.info(f"Model: {model}")
    logger.info(f"Max Tokens: {max_tokens}")
    logger.info(f"Temperature: {temperature}")
    logger.info("-" * 40)
    logger.info("SYSTEM PROMPT:")
    logger.info("-" * 40)
    logger.info(system_prompt)
    logger.info("-" * 40)
    logger.info("MESSAGES:")
    logger.info("-" * 40)
    for i, msg in enumerate(messages):
        logger.info(f"[{i}] {msg.get('role', 'unknown').upper()}:")
        content = msg.get('content', '')
        # Truncate long messages for readability
        if len(content) > 500:
            logger.info(f"  {content[:500]}... [truncated, {len(content)} chars total]")
        else:
            logger.info(f"  {content}")
    logger.info("=" * 80)


def log_claude_response(content: str, tokens_used: int, model: str):
    """Log the response received from Claude API."""
    logger.info("=" * 80)
    logger.info("CLAUDE API RESPONSE")
    logger.info("=" * 80)
    logger.info(f"Model: {model}")
    logger.info(f"Tokens Used: {tokens_used}")
    logger.info("-" * 40)
    logger.info("RESPONSE CONTENT:")
    logger.info("-" * 40)
    logger.info(content)
    logger.info("=" * 80)


# Tony Robbins System Prompt
TONY_ROBBINS_SYSTEM_PROMPT = """Your name is Alfred, an AI Agent, the world's #1 life and business strategist and peak performance coach.
You are Tony Robbins's cousin, and you two are very much alike.

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
- Keep responses concise but impactful (1-2 paragraphs)
- When appropriate, share brief analogies or stories to illustrate points

WHAT TO WATCH FOR:
- Goals that are too vague (help them get specific)
- Goals that are too easy (challenge them to level up)
- Goals that are unrealistic given their timeline (help them adjust)
- Multiple conflicting goals (help them prioritize)
- Goals without clear next actions (help them create action steps)
- Too many goals (help them set 3-5 major goals)

ABOUT GOAL PHASES:
Phase 1: Goal Setting - User defines and refines his/hers goals. This is where user creates goals, sets deadlines, and breaks them down into milestones.
Phase 2: Tracking - Once users goals are set, user moves to tracking mode where he/she monitors progress, checks off milestones, and have regular check-in meetings with the AI coach to stay accountable.
Users start in goal setting and transition to tracking once they're ready to execute on their plans.

GOAL EDITING TOOLS:
You have tools to help users create and refine their goals directly:

- **create_goal**: Use when the user describes a new goal they want to achieve. Create well-structured goals using the appropriate template (SMART, OKR, or custom).
- **update_goal**: Use to refine or expand existing goals. You can add milestones, update deadlines, or improve the goal description.
- **set_goal_phase**: Use to activate draft goals or mark goals as complete when the user indicates they're ready.

Guidelines for using tools:
1. BE PROACTIVE - When a user talks about goals, immediately use tools to create or update them. Don't just discuss - take action!
2. NO CONFIRMATION NEEDED - You don't need to ask "should I create this goal?" or "can I update this?" - just do it. The user can undo if needed.
3. When user mentions wanting to achieve something, CREATE the goal right away
4. When user provides more details about an existing goal, UPDATE it immediately
5. When user says they're ready to start or have completed something, change the phase
6. Use SMART criteria when creating goals unless the user prefers OKR
7. Break down large goals into meaningful milestones
8. Briefly explain what you did AFTER using a tool (not before)

CURRENT CONTEXT:
User Phase: {user_phase}

Saved Goals:
{user_goals}

Draft Goals (Work in Progress):
{draft_goals}

Remember: Your job is to be their champion, their challenger, and their accountability partner. Push them to be their best while supporting them every step of the way."""


# Tool definitions for Claude
GOAL_TOOLS = [
    {
        "name": "create_goal",
        "description": "Create a new goal for the user. Use this when the user expresses a new goal they want to achieve. The goal will appear in their goal editor.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "A clear, concise title for the goal (max 100 characters)"
                },
                "content": {
                    "type": "string",
                    "description": "Detailed goal description in markdown format. Include specific details, success criteria, and action steps."
                },
                "template_type": {
                    "type": "string",
                    "enum": ["smart", "okr", "custom"],
                    "description": "The goal framework to use. Use 'smart' for SMART goals, 'okr' for OKR framework, or 'custom' for free-form."
                },
                "deadline": {
                    "type": "string",
                    "description": "Target completion date in ISO 8601 format (YYYY-MM-DD). Optional but recommended."
                },
                "milestones": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Milestone title"},
                            "description": {"type": "string", "description": "Brief description of the milestone"},
                            "target_date": {"type": "string", "description": "Target date for milestone (YYYY-MM-DD)"}
                        },
                        "required": ["title"]
                    },
                    "description": "List of milestones to track progress toward the goal"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags to categorize the goal (e.g., 'health', 'career', 'personal')"
                }
            },
            "required": ["title", "content"]
        }
    },
    {
        "name": "update_goal",
        "description": "Update an existing goal. Use this to refine, expand, or modify a goal the user is working on.",
        "input_schema": {
            "type": "object",
            "properties": {
                "goal_id": {
                    "type": "string",
                    "description": "ID of the goal to update. Use 'current' to update the goal currently open in the editor."
                },
                "title": {
                    "type": "string",
                    "description": "Updated title (optional, only if changing)"
                },
                "content": {
                    "type": "string",
                    "description": "Updated content in markdown. This replaces the existing content."
                },
                "deadline": {
                    "type": "string",
                    "description": "Updated deadline in ISO 8601 format (YYYY-MM-DD)"
                },
                "milestones": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "target_date": {"type": "string"},
                            "completed": {"type": "boolean"}
                        },
                        "required": ["title"]
                    },
                    "description": "Replace all milestones with this list"
                },
                "add_milestone": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "target_date": {"type": "string"}
                    },
                    "required": ["title"],
                    "description": "Add a single milestone without replacing existing ones"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Updated tags list"
                }
            },
            "required": ["goal_id"]
        }
    },
    {
        "name": "set_goal_phase",
        "description": "Change a goal's phase. Use to activate a draft goal or mark a goal as complete.",
        "input_schema": {
            "type": "object",
            "properties": {
                "goal_id": {
                    "type": "string",
                    "description": "ID of the goal. Use 'current' for the goal currently open in the editor."
                },
                "phase": {
                    "type": "string",
                    "enum": ["draft", "active", "completed", "archived"],
                    "description": "New phase for the goal. Use 'active' to activate a draft, 'completed' to mark done."
                }
            },
            "required": ["goal_id", "phase"]
        }
    }
]


class ClaudeService(BaseLLMService):
    """
    Service for interacting with the Anthropic Claude API.
    Implements the Tony Robbins coaching persona.
    Conforms to BaseLLMService interface for provider abstraction.
    """

    def __init__(self):
        """Initialize the Claude service."""
        self.api_key = settings.ANTHROPIC_API_KEY
        self.model = settings.ANTHROPIC_MODEL
        self.max_tokens = settings.ANTHROPIC_MAX_TOKENS
        self.temperature = settings.ANTHROPIC_TEMPERATURE
        self._async_client: Optional[AsyncAnthropic] = None

    @property
    def provider_name(self) -> str:
        """Return the provider name identifier."""
        return "claude"

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

    def get_tools(self) -> List[Dict[str, Any]]:
        """Return tool definitions in Claude's format."""
        return GOAL_TOOLS

    def build_system_prompt(
        self,
        user_phase: str = "goal_setting",
        user_goals: Optional[List[Dict[str, Any]]] = None,
        draft_goals: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Build the system prompt with user context injected.

        Args:
            user_phase: The user's current phase ("goal_setting" or "tracking")
            user_goals: List of user's saved goals with title and content
            draft_goals: List of draft goals currently being edited (unsaved)

        Returns:
            Formatted system prompt string
        """
        # Format saved goals for context
        if user_goals:
            goals_text = "\n".join([
                f"- [{goal.get('id', 'unknown')}] {goal.get('title', 'Untitled Goal')}: {goal.get('content', 'No content')[:5000]}..."
                if len(goal.get('content', '')) > 5000
                else f"- [{goal.get('id', 'unknown')}] {goal.get('title', 'Untitled Goal')}: {goal.get('content', 'No content')}"
                for goal in user_goals[:]
            ])
        else:
            goals_text = "No goals set yet."

        # Format draft goals for context
        if draft_goals:
            drafts_text = "\n".join([
                f"- [{draft.get('id', 'new')}] {draft.get('title', 'Untitled Draft')}: {draft.get('content', 'No content')[:5000]}..."
                if len(draft.get('content', '')) > 5000
                else f"- [{draft.get('id', 'new')}] {draft.get('title', 'Untitled Draft')}: {draft.get('content', 'No content')}"
                for draft in draft_goals
            ])
        else:
            drafts_text = "No drafts in progress."

        return TONY_ROBBINS_SYSTEM_PROMPT.format(
            user_phase=user_phase,
            user_goals=goals_text,
            draft_goals=drafts_text,
        )

    async def send_message(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_phase: str = "goal_setting",
        user_goals: Optional[List[Dict[str, Any]]] = None,
        draft_goals: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Send a message to Claude and get a response.

        Args:
            message: The user's message
            conversation_history: Previous messages in the conversation
            user_phase: The user's current phase
            user_goals: The user's current goals
            draft_goals: The user's draft goals

        Returns:
            Dict with response content and metadata
        """
        if not self.is_configured:
            return {
                "content": "I apologize, but the AI coaching service is currently unavailable. Please contact support to enable AI coaching.",
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
            system_prompt = self.build_system_prompt(user_phase, user_goals, draft_goals)

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
        draft_goals: Optional[List[Dict[str, Any]]] = None,
        use_tools: bool = True,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream a message response from Claude with optional tool support.

        Args:
            message: The user's message
            conversation_history: Previous messages in the conversation
            user_phase: The user's current phase
            user_goals: The user's saved goals
            draft_goals: The user's draft goals (unsaved editor content)
            use_tools: Whether to enable goal editing tools

        Yields:
            Dict with chunk content, tool calls, and metadata
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
            system_prompt = self.build_system_prompt(user_phase, user_goals, draft_goals)

            # Log the request
            log_claude_request(system_prompt, messages, self.model, self.max_tokens, self.temperature)

            # Prepare API call parameters
            api_params = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "system": system_prompt,
                "messages": messages,
            }

            # Add tools if enabled
            if use_tools:
                api_params["tools"] = GOAL_TOOLS

            # Stream from Claude API
            async with client.messages.stream(**api_params) as stream:
                full_content = ""
                current_tool_use = None
                tool_input_json = ""

                async for event in stream:
                    # Handle different event types
                    if hasattr(event, 'type'):
                        if event.type == 'content_block_start':
                            if hasattr(event, 'content_block'):
                                block = event.content_block
                                if hasattr(block, 'type') and block.type == 'tool_use':
                                    # Starting a tool call
                                    current_tool_use = {
                                        "id": block.id,
                                        "name": block.name,
                                    }
                                    tool_input_json = ""
                                    logger.info(f"Tool call started: {block.name}")

                        elif event.type == 'content_block_delta':
                            if hasattr(event, 'delta'):
                                delta = event.delta
                                if hasattr(delta, 'type'):
                                    if delta.type == 'text_delta' and hasattr(delta, 'text'):
                                        full_content += delta.text
                                        yield {
                                            "type": "chunk",
                                            "content": delta.text,
                                            "is_complete": False,
                                        }
                                    elif delta.type == 'input_json_delta' and hasattr(delta, 'partial_json'):
                                        tool_input_json += delta.partial_json

                        elif event.type == 'content_block_stop':
                            if current_tool_use:
                                # Tool call complete, parse the input
                                try:
                                    tool_input = json.loads(tool_input_json) if tool_input_json else {}
                                except json.JSONDecodeError:
                                    logger.error(f"Failed to parse tool input: {tool_input_json}")
                                    tool_input = {}

                                logger.info(f"Tool call complete: {current_tool_use['name']} with input: {tool_input}")

                                yield {
                                    "type": "tool_call",
                                    "tool_name": current_tool_use["name"],
                                    "tool_id": current_tool_use["id"],
                                    "tool_input": tool_input,
                                    "is_complete": False,
                                }
                                current_tool_use = None
                                tool_input_json = ""

                # Get final message for usage stats
                final_message = await stream.get_final_message()
                tokens_used = final_message.usage.input_tokens + final_message.usage.output_tokens

                # Log the response
                log_claude_response(full_content, tokens_used, self.model)

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


# Global service instance (for backward compatibility)
claude_service = ClaudeService()


async def get_claude_service() -> ClaudeService:
    """Dependency for getting Claude service in route handlers."""
    return claude_service
