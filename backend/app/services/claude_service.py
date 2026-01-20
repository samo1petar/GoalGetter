"""
Claude AI service compatibility shim.

This module provides backward compatibility for code that imports from the old location.
The actual implementation has been moved to app.services.llm.claude_service.

DEPRECATED: Import from app.services.llm instead.
"""
import warnings

warnings.warn(
    "Importing from app.services.claude_service is deprecated. "
    "Use app.services.llm.claude_service instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from the new location for backward compatibility
from app.services.llm.claude_service import (
    ClaudeService,
    claude_service,
    get_claude_service,
    GOAL_TOOLS,
    TONY_ROBBINS_SYSTEM_PROMPT,
    log_claude_request,
    log_claude_response,
)

__all__ = [
    "ClaudeService",
    "claude_service",
    "get_claude_service",
    "GOAL_TOOLS",
    "TONY_ROBBINS_SYSTEM_PROMPT",
    "log_claude_request",
    "log_claude_response",
]
