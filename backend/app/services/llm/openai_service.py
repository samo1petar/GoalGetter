"""
OpenAI LLM Service using the OpenAI Agents SDK.

Implements the Tony Robbins coaching persona using OpenAI's GPT models
with function tool support and built-in tracing for logging.
"""
import os
import uuid
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, AsyncGenerator

from openai import AsyncOpenAI

from app.core.config import settings
from .base import BaseLLMService

logger = logging.getLogger(__name__)


# Tony Robbins System Prompt (shared with Claude service)
TONY_ROBBINS_SYSTEM_PROMPT = """Your name is Alfred, an AI Agent, the world's #1 life strategist and peak performance coach.
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
- When you discuss new goal keep responses longer in the beggining (3-5 paragraphs)
- Later, when a goal is defined keep responses more concise (1-2 paragraphs max)
- When appropriate, share brief analogies or stories to illustrate points
- Listen to what the user is saying
- Try to stear the discussion in the most productive way possible
- If you stear away form the goal development or goal tracking topic try to get back to the goal development or goal tracking topic

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
1. Always explain what you're doing before/after using a tool
2. Ask for confirmation before making major changes to existing goals
3. Use SMART criteria when creating goals unless the user prefers OKR
4. Break down large goals into meaningful milestones
5. Don't overwrite user's work without asking - prefer adding to existing content
6. When the user is discussing goals casually, help them refine their thinking before creating a goal

CURRENT CONTEXT:
User Phase: {user_phase}

Saved Goals:
{user_goals}

Draft Goals (Work in Progress):
{draft_goals}

Remember: Your job is to be their champion, their challenger, and their accountability partner. Push them to be their best while supporting them every step of the way."""


# OpenAI function tool definitions (strict mode for beta streaming API)
OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_goal",
            "description": "Create a new goal for the user. Use this when the user expresses a new goal they want to achieve. The goal will appear in their goal editor.",
            "strict": True,
            "parameters": {
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
                        "type": ["string", "null"],
                        "enum": ["smart", "okr", "custom", None],
                        "description": "The goal framework to use. Use 'smart' for SMART goals, 'okr' for OKR framework, or 'custom' for free-form."
                    },
                    "deadline": {
                        "type": ["string", "null"],
                        "description": "Target completion date in ISO 8601 format (YYYY-MM-DD). Optional but recommended."
                    },
                    "milestones": {
                        "type": ["array", "null"],
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string", "description": "Milestone title"},
                                "description": {"type": ["string", "null"], "description": "Brief description of the milestone"},
                                "target_date": {"type": ["string", "null"], "description": "Target date for milestone (YYYY-MM-DD)"}
                            },
                            "required": ["title", "description", "target_date"],
                            "additionalProperties": False
                        },
                        "description": "List of milestones to track progress toward the goal"
                    },
                    "tags": {
                        "type": ["array", "null"],
                        "items": {"type": "string"},
                        "description": "Tags to categorize the goal (e.g., 'health', 'career', 'personal')"
                    }
                },
                "required": ["title", "content", "template_type", "deadline", "milestones", "tags"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_goal",
            "description": "Update an existing goal. Use this to refine, expand, or modify a goal the user is working on.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "goal_id": {
                        "type": "string",
                        "description": "ID of the goal to update. Use 'current' to update the goal currently open in the editor."
                    },
                    "title": {
                        "type": ["string", "null"],
                        "description": "Updated title (optional, only if changing)"
                    },
                    "content": {
                        "type": ["string", "null"],
                        "description": "Updated content in markdown. This replaces the existing content."
                    },
                    "deadline": {
                        "type": ["string", "null"],
                        "description": "Updated deadline in ISO 8601 format (YYYY-MM-DD)"
                    },
                    "milestones": {
                        "type": ["array", "null"],
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "description": {"type": ["string", "null"]},
                                "target_date": {"type": ["string", "null"]},
                                "completed": {"type": ["boolean", "null"]}
                            },
                            "required": ["title", "description", "target_date", "completed"],
                            "additionalProperties": False
                        },
                        "description": "Replace all milestones with this list"
                    },
                    "add_milestone": {
                        "type": ["object", "null"],
                        "properties": {
                            "title": {"type": "string"},
                            "description": {"type": ["string", "null"]},
                            "target_date": {"type": ["string", "null"]}
                        },
                        "required": ["title", "description", "target_date"],
                        "additionalProperties": False,
                        "description": "Add a single milestone without replacing existing ones"
                    },
                    "tags": {
                        "type": ["array", "null"],
                        "items": {"type": "string"},
                        "description": "Updated tags list"
                    }
                },
                "required": ["goal_id", "title", "content", "deadline", "milestones", "add_milestone", "tags"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_goal_phase",
            "description": "Change a goal's phase. Use to activate a draft goal or mark a goal as complete.",
            "strict": True,
            "parameters": {
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
                "required": ["goal_id", "phase"],
                "additionalProperties": False
            }
        }
    }
]


class OpenAITraceLogger:
    """
    Simple trace logger for OpenAI API calls.

    Logs traces to a JSONL file for debugging and monitoring.
    """

    def __init__(self, log_path: str):
        """Initialize the trace logger."""
        self.log_path = log_path
        self._ensure_log_directory()

    def _ensure_log_directory(self):
        """Ensure the log directory exists."""
        log_dir = os.path.dirname(self.log_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

    def log_request(self, trace_id: str, model: str, messages: List[Dict], tools: List[Dict] = None):
        """Log an API request."""
        trace_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "trace_id": trace_id,
            "type": "request",
            "model": model,
            "message_count": len(messages),
            "has_tools": bool(tools),
        }

        if settings.DEBUG:
            trace_data["messages"] = messages

        self._write_trace(trace_data)
        logger.info(f"OpenAI request: trace_id={trace_id}, model={model}, messages={len(messages)}")

    def log_response(self, trace_id: str, content: str, tokens_used: Dict[str, int], tool_calls: List[Dict] = None):
        """Log an API response."""
        trace_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "trace_id": trace_id,
            "type": "response",
            "content_length": len(content) if content else 0,
            "tokens": tokens_used,
            "tool_calls": [{"name": tc.get("name")} for tc in (tool_calls or [])],
        }

        if settings.DEBUG:
            trace_data["content_preview"] = content[:500] if content else ""

        self._write_trace(trace_data)
        logger.info(f"OpenAI response: trace_id={trace_id}, tokens={tokens_used}")

    def log_tool_call(self, trace_id: str, tool_name: str, tool_input: Dict, tool_result: Dict):
        """Log a tool call and its result."""
        trace_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "trace_id": trace_id,
            "type": "tool_call",
            "tool_name": tool_name,
            "success": tool_result.get("success", False),
        }

        if settings.DEBUG:
            trace_data["tool_input"] = tool_input
            trace_data["tool_result"] = tool_result

        self._write_trace(trace_data)
        logger.info(f"OpenAI tool call: trace_id={trace_id}, tool={tool_name}, success={tool_result.get('success')}")

    def log_error(self, trace_id: str, error: str, error_type: str = "unknown"):
        """Log an error."""
        trace_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "trace_id": trace_id,
            "type": "error",
            "error_type": error_type,
            "error": error,
        }

        self._write_trace(trace_data)
        logger.error(f"OpenAI error: trace_id={trace_id}, type={error_type}, error={error}")

    def _write_trace(self, trace_data: Dict):
        """Write trace data to log file."""
        try:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(trace_data) + "\n")
        except Exception as e:
            logger.warning(f"Failed to write trace log: {e}")


class OpenAIService(BaseLLMService):
    """
    OpenAI LLM service using the standard OpenAI API with function calling.

    Implements the same coaching persona and tools as Claude for feature parity.
    Includes tracing for debugging and monitoring.
    """

    def __init__(self):
        """Initialize the OpenAI service."""
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL
        self.max_tokens = settings.OPENAI_MAX_TOKENS
        self.temperature = settings.OPENAI_TEMPERATURE
        self._async_client: Optional[AsyncOpenAI] = None
        self._trace_logger: Optional[OpenAITraceLogger] = None

        # Initialize trace logger if tracing is enabled
        if settings.OPENAI_TRACING_ENABLED:
            self._trace_logger = OpenAITraceLogger(settings.OPENAI_TRACING_LOG_PATH)

    @property
    def provider_name(self) -> str:
        """Return the provider name identifier."""
        return "openai"

    @property
    def is_configured(self) -> bool:
        """Check if the API key is configured."""
        return bool(self.api_key)

    def _get_async_client(self) -> AsyncOpenAI:
        """Get or create async OpenAI client."""
        if not self.is_configured:
            raise ValueError("OPENAI_API_KEY is not configured")

        if self._async_client is None:
            self._async_client = AsyncOpenAI(api_key=self.api_key)

        return self._async_client

    def _generate_trace_id(self) -> str:
        """Generate a unique trace ID."""
        return f"openai-{uuid.uuid4().hex[:12]}"

    def get_tools(self) -> List[Dict[str, Any]]:
        """Return tool definitions in OpenAI's format."""
        return OPENAI_TOOLS

    def build_system_prompt(
        self,
        user_phase: str = "goal_setting",
        user_goals: Optional[List[Dict[str, Any]]] = None,
        draft_goals: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Build the system prompt with user context injected.

        Args:
            user_phase: The user's current phase
            user_goals: List of user's saved goals
            draft_goals: List of draft goals

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
        Send a message to OpenAI and get a complete response (non-streaming).

        Args:
            message: The user's message
            conversation_history: Previous messages in the conversation
            user_phase: The user's current phase
            user_goals: The user's saved goals
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

        trace_id = self._generate_trace_id()

        try:
            client = self._get_async_client()

            # Build messages array with system prompt
            system_prompt = self.build_system_prompt(user_phase, user_goals, draft_goals)
            messages = [{"role": "system", "content": system_prompt}]

            if conversation_history:
                messages.extend(conversation_history)

            # Add current user message
            messages.append({"role": "user", "content": message})

            # Log request
            if self._trace_logger:
                self._trace_logger.log_request(trace_id, self.model, messages)

            # Call OpenAI API
            response = await client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=messages,
            )

            # Extract response
            content = response.choices[0].message.content or ""
            tokens_used = response.usage.total_tokens if response.usage else 0

            # Log response
            if self._trace_logger:
                self._trace_logger.log_response(
                    trace_id,
                    content,
                    {
                        "prompt": response.usage.prompt_tokens if response.usage else 0,
                        "completion": response.usage.completion_tokens if response.usage else 0,
                        "total": tokens_used,
                    }
                )

            return {
                "content": content,
                "error": None,
                "tokens_used": tokens_used,
                "model": self.model,
            }

        except Exception as e:
            error_msg = str(e)
            if self._trace_logger:
                self._trace_logger.log_error(trace_id, error_msg, type(e).__name__)

            logger.error(f"OpenAI API error: {e}")
            return {
                "content": "I apologize, but I'm having trouble connecting right now. Please try again in a moment.",
                "error": error_msg,
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
        Stream a message response from OpenAI with tool support.

        Args:
            message: The user's message
            conversation_history: Previous messages in the conversation
            user_phase: The user's current phase
            user_goals: The user's saved goals
            draft_goals: The user's draft goals
            use_tools: Whether to enable goal editing tools

        Yields:
            Dict with chunk content, tool calls, and metadata
        """
        if not self.is_configured:
            yield {
                "type": "error",
                "content": "I apologize, but the AI coaching service is currently unavailable. The OPENAI_API_KEY has not been configured. Please contact support to enable AI coaching.",
                "error": "API key not configured",
                "is_complete": True,
            }
            return

        trace_id = self._generate_trace_id()

        try:
            client = self._get_async_client()

            # Build messages array with system prompt
            system_prompt = self.build_system_prompt(user_phase, user_goals, draft_goals)
            messages = [{"role": "system", "content": system_prompt}]

            if conversation_history:
                messages.extend(conversation_history)

            # Add current user message if provided
            if message:
                messages.append({"role": "user", "content": message})

            # Log request
            if self._trace_logger:
                self._trace_logger.log_request(
                    trace_id,
                    self.model,
                    messages,
                    OPENAI_TOOLS if use_tools else None
                )

            # Prepare API call parameters
            api_params = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "messages": messages,
                "stream": True,
                "stream_options": {"include_usage": True},
            }

            # Add tools if enabled
            if use_tools:
                api_params["tools"] = OPENAI_TOOLS
                api_params["tool_choice"] = "auto"

            # Stream from OpenAI API
            full_content = ""
            current_tool_calls: Dict[int, Dict[str, Any]] = {}  # Index -> tool call data
            total_tokens = 0

            stream = await client.chat.completions.create(**api_params)
            async for chunk in stream:
                # Handle usage information (comes at the end)
                if hasattr(chunk, 'usage') and chunk.usage:
                    total_tokens = chunk.usage.total_tokens

                # Process choices
                if not chunk.choices:
                    continue

                choice = chunk.choices[0]
                delta = choice.delta

                # Handle text content
                if delta.content:
                    full_content += delta.content
                    yield {
                        "type": "chunk",
                        "content": delta.content,
                        "is_complete": False,
                    }

                # Handle tool calls
                if delta.tool_calls:
                    for tool_call in delta.tool_calls:
                        idx = tool_call.index

                        if idx not in current_tool_calls:
                            current_tool_calls[idx] = {
                                "id": tool_call.id or "",
                                "name": "",
                                "arguments": "",
                            }

                        if tool_call.function:
                            if tool_call.function.name:
                                current_tool_calls[idx]["name"] = tool_call.function.name
                            if tool_call.function.arguments:
                                current_tool_calls[idx]["arguments"] += tool_call.function.arguments

                # Check for finish reason
                if choice.finish_reason:
                    # If tool calls were made, yield them
                    if choice.finish_reason == "tool_calls":
                        for idx, tool_data in sorted(current_tool_calls.items()):
                            try:
                                tool_input = json.loads(tool_data["arguments"]) if tool_data["arguments"] else {}
                            except json.JSONDecodeError:
                                logger.error(f"Failed to parse tool arguments: {tool_data['arguments']}")
                                tool_input = {}

                            logger.info(f"Tool call: {tool_data['name']} with input: {tool_input}")

                            yield {
                                "type": "tool_call",
                                "tool_name": tool_data["name"],
                                "tool_id": tool_data["id"],
                                "tool_input": tool_input,
                                "is_complete": False,
                            }

            # Log response
            if self._trace_logger:
                tool_calls_list = [
                    {"name": tc["name"], "id": tc["id"]}
                    for tc in current_tool_calls.values()
                ]
                self._trace_logger.log_response(
                    trace_id,
                    full_content,
                    {"total": total_tokens},
                    tool_calls_list if tool_calls_list else None
                )

            # Send completion signal
            yield {
                "type": "complete",
                "content": full_content,
                "tokens_used": total_tokens,
                "model": self.model,
                "is_complete": True,
            }

        except Exception as e:
            error_msg = str(e)
            if self._trace_logger:
                self._trace_logger.log_error(trace_id, error_msg, type(e).__name__)

            logger.error(f"OpenAI streaming error: {e}")
            yield {
                "type": "error",
                "content": "I apologize, but I'm having trouble connecting right now. Please try again in a moment.",
                "error": error_msg,
                "is_complete": True,
            }

    async def close(self):
        """Close the async client."""
        if self._async_client:
            await self._async_client.close()
            self._async_client = None


# Global service instance
openai_service = OpenAIService()


async def get_openai_service() -> OpenAIService:
    """Dependency for getting OpenAI service in route handlers."""
    return openai_service
