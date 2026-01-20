"""
Base LLM Service Interface.

Defines the abstract interface that all LLM service providers must implement.
This ensures feature parity across different providers (Claude, OpenAI, etc.).
"""
from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Dict, Any, Optional


class BaseLLMService(ABC):
    """
    Abstract base class for LLM service providers.

    All LLM providers (Claude, OpenAI, etc.) must implement this interface
    to ensure consistent behavior across the application.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Return the provider name identifier.

        Returns:
            str: Provider name (e.g., 'claude', 'openai')
        """
        pass

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """
        Check if the provider is properly configured with API keys.

        Returns:
            bool: True if the provider has valid configuration
        """
        pass

    @abstractmethod
    async def send_message(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_phase: str = "goal_setting",
        user_goals: Optional[List[Dict[str, Any]]] = None,
        draft_goals: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Send a message and get a complete response (non-streaming).

        Args:
            message: The user's message content
            conversation_history: Previous messages in the conversation
            user_phase: The user's current phase ("goal_setting" or "tracking")
            user_goals: List of user's saved goals for context
            draft_goals: List of draft goals currently being edited

        Returns:
            Dict containing:
                - content: The response text
                - error: Error message if any, else None
                - tokens_used: Number of tokens consumed
                - model: The model used for generation
        """
        pass

    @abstractmethod
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
        Stream a message response with tool call support.

        Args:
            message: The user's message content
            conversation_history: Previous messages in the conversation
            user_phase: The user's current phase
            user_goals: List of user's saved goals for context
            draft_goals: List of draft goals currently being edited
            use_tools: Whether to enable goal editing tools

        Yields:
            Dict with event data. Event types include:
                - chunk: Partial text content
                    - type: "chunk"
                    - content: Partial text
                    - is_complete: False
                - tool_call: Tool invocation
                    - type: "tool_call"
                    - tool_name: Name of the tool
                    - tool_id: Unique identifier for the tool call
                    - tool_input: Tool parameters
                    - is_complete: False
                - complete: Final message
                    - type: "complete"
                    - content: Full response text
                    - tokens_used: Total tokens consumed
                    - model: Model used
                    - is_complete: True
                - error: Error occurred
                    - type: "error"
                    - content: Error message
                    - error: Detailed error info
                    - is_complete: True
        """
        pass

    @abstractmethod
    def get_tools(self) -> List[Dict[str, Any]]:
        """
        Return tool definitions in provider-specific format.

        Returns:
            List of tool definitions. The format depends on the provider:
                - Claude: Uses input_schema with JSON Schema
                - OpenAI: Uses function definitions or decorated functions
        """
        pass

    @abstractmethod
    def build_system_prompt(
        self,
        user_phase: str = "goal_setting",
        user_goals: Optional[List[Dict[str, Any]]] = None,
        draft_goals: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Build the system prompt with context injection.

        Args:
            user_phase: The user's current phase
            user_goals: List of user's saved goals
            draft_goals: List of draft goals

        Returns:
            Formatted system prompt string with user context
        """
        pass

    async def close(self) -> None:
        """
        Clean up resources (close HTTP clients, etc.).

        Override this method if the provider needs cleanup.
        Default implementation does nothing.
        """
        pass
