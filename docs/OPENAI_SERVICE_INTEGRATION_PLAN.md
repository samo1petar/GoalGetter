# OpenAI Service Integration Plan

This document outlines the detailed plan for adding OpenAI as an alternative LLM provider alongside the existing Claude service in GoalGetter. The implementation uses the **OpenAI Agents SDK** for agent-based interactions with built-in tracing for logging.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Changes](#architecture-changes)
3. [Backend Implementation](#backend-implementation)
4. [Frontend Implementation](#frontend-implementation)
5. [Configuration & Environment](#configuration--environment)
6. [OpenAI Agents SDK Integration](#openai-agents-sdk-integration)
7. [Tracing & Logging](#tracing--logging)
8. [Migration Strategy](#migration-strategy)
9. [Testing Plan](#testing-plan)
10. [File Change Summary](#file-change-summary)

---

## Overview

### Goals

- Add OpenAI as an alternative LLM provider using the **OpenAI Agents SDK**
- Keep Claude as the existing provider (no removal)
- Allow users to choose between Claude and OpenAI
- Leverage OpenAI Agents SDK traces for comprehensive logging
- Maintain feature parity (streaming, tool calls for goals)

### Current State

The application currently uses:
- `ClaudeService` singleton in `backend/app/services/claude_service.py`
- Direct Anthropic SDK integration with `AsyncAnthropic` client
- Three tools: `create_goal`, `update_goal`, `set_goal_phase`
- WebSocket streaming for real-time responses
- `GoalToolHandler` for executing tool calls

### Target State

- Abstract LLM service interface (`BaseLLMService`)
- `ClaudeService` and `OpenAIService` implementations
- Provider selection stored per-user or per-request
- Unified tool execution via existing `GoalToolHandler`
- OpenAI Agents SDK with tracing enabled

---

## Architecture Changes

### Service Layer Abstraction

```
backend/app/services/
├── llm/
│   ├── __init__.py           # Exports factory and base class
│   ├── base.py               # BaseLLMService abstract class
│   ├── claude_service.py     # Refactored Claude implementation
│   ├── openai_service.py     # New OpenAI Agents SDK implementation
│   └── factory.py            # LLM service factory
├── goal_tool_handler.py      # Existing (shared by both providers)
└── ...
```

### Base Service Interface

```python
# backend/app/services/llm/base.py
from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Dict, Any, Optional

class BaseLLMService(ABC):
    """Abstract base class for LLM service providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'claude', 'openai')."""
        pass

    @abstractmethod
    async def send_message(
        self,
        messages: List[Dict[str, str]],
        user_phase: str,
        saved_goals: List[Dict[str, Any]] = None,
        draft_goals: List[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send a message and get a complete response (non-streaming)."""
        pass

    @abstractmethod
    async def stream_message(
        self,
        messages: List[Dict[str, str]],
        user_phase: str,
        saved_goals: List[Dict[str, Any]] = None,
        draft_goals: List[Dict[str, Any]] = None,
        active_goal_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream a message response with tool call support."""
        pass

    @abstractmethod
    def get_tools(self) -> List[Dict[str, Any]]:
        """Return tool definitions in provider-specific format."""
        pass

    @abstractmethod
    def build_system_prompt(
        self,
        user_phase: str,
        saved_goals: List[Dict[str, Any]] = None,
        draft_goals: List[Dict[str, Any]] = None,
    ) -> str:
        """Build the system prompt with context injection."""
        pass
```

### Factory Pattern

```python
# backend/app/services/llm/factory.py
from typing import Literal
from .base import BaseLLMService
from .claude_service import ClaudeService
from .openai_service import OpenAIService

LLMProvider = Literal["claude", "openai"]

class LLMServiceFactory:
    _instances: Dict[str, BaseLLMService] = {}

    @classmethod
    def get_service(cls, provider: LLMProvider = "claude") -> BaseLLMService:
        """Get or create an LLM service instance for the specified provider."""
        if provider not in cls._instances:
            if provider == "claude":
                cls._instances[provider] = ClaudeService()
            elif provider == "openai":
                cls._instances[provider] = OpenAIService()
            else:
                raise ValueError(f"Unknown LLM provider: {provider}")
        return cls._instances[provider]

    @classmethod
    def get_available_providers(cls) -> List[str]:
        """Return list of configured providers with valid API keys."""
        providers = []
        if settings.ANTHROPIC_API_KEY:
            providers.append("claude")
        if settings.OPENAI_API_KEY:
            providers.append("openai")
        return providers
```

---

## Backend Implementation

### 1. New OpenAI Service (`backend/app/services/llm/openai_service.py`)

```python
from openai import AsyncOpenAI
from agents import Agent, Runner, function_tool, trace
from agents.tracing import TracingProcessor
from typing import AsyncGenerator, List, Dict, Any, Optional
import json
import logging

from app.core.config import settings
from .base import BaseLLMService

logger = logging.getLogger(__name__)

class OpenAIService(BaseLLMService):
    """OpenAI LLM service using Agents SDK."""

    def __init__(self):
        self._client: Optional[AsyncOpenAI] = None
        self._agent: Optional[Agent] = None
        self._setup_tracing()

    def _setup_tracing(self):
        """Configure OpenAI Agents SDK tracing."""
        # Enable tracing for all agent runs
        trace.set_processor(TracingProcessor(
            service_name="goalgetter",
            export_to_console=settings.DEBUG,
            export_to_file=True,
            file_path="logs/openai_traces.jsonl"
        ))

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def _create_agent(self, system_prompt: str) -> Agent:
        """Create an Agent with goal management tools."""
        return Agent(
            name="GoalGetter Coach",
            model=settings.OPENAI_MODEL,
            instructions=system_prompt,
            tools=[
                self._create_goal_tool(),
                self._update_goal_tool(),
                self._set_goal_phase_tool(),
            ],
        )

    @function_tool
    async def _create_goal_tool(
        self,
        title: str,
        content: str,
        template_type: str = "custom",
        deadline: Optional[str] = None,
        milestones: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """Create a new goal for the user."""
        # Tool implementation delegates to GoalToolHandler
        pass

    @function_tool
    async def _update_goal_tool(
        self,
        goal_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        deadline: Optional[str] = None,
        milestones: Optional[List[Dict]] = None,
        add_milestone: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Update an existing goal."""
        pass

    @function_tool
    async def _set_goal_phase_tool(
        self,
        goal_id: str,
        phase: str,
    ) -> Dict[str, Any]:
        """Change the phase of a goal."""
        pass

    async def stream_message(
        self,
        messages: List[Dict[str, str]],
        user_phase: str,
        saved_goals: List[Dict[str, Any]] = None,
        draft_goals: List[Dict[str, Any]] = None,
        active_goal_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream response using OpenAI Agents SDK with tracing."""

        system_prompt = self.build_system_prompt(user_phase, saved_goals, draft_goals)

        # Create agent with tools
        agent = self._create_agent(system_prompt)

        # Use Runner.run_streamed for streaming responses
        with trace.span("chat_message"):
            runner = Runner(agent)

            async for event in runner.run_streamed(
                messages=messages,
                context={"active_goal_id": active_goal_id}
            ):
                if event.type == "text_delta":
                    yield {
                        "type": "content",
                        "content": event.delta,
                    }
                elif event.type == "tool_call":
                    yield {
                        "type": "tool_call",
                        "tool_name": event.tool_name,
                        "tool_input": event.tool_input,
                    }
                elif event.type == "tool_result":
                    yield {
                        "type": "tool_result",
                        "tool_name": event.tool_name,
                        "result": event.result,
                    }
                elif event.type == "done":
                    yield {
                        "type": "done",
                        "usage": {
                            "input_tokens": event.usage.input_tokens,
                            "output_tokens": event.usage.output_tokens,
                        }
                    }
```

### 2. Refactor Claude Service

Move existing `claude_service.py` to `backend/app/services/llm/claude_service.py` and update to implement `BaseLLMService`:

**Changes Required:**
- Add `from .base import BaseLLMService`
- Add `class ClaudeService(BaseLLMService):`
- Add `@property def provider_name(self) -> str: return "claude"`
- Ensure method signatures match the abstract base class
- Keep all existing functionality

### 3. Update Chat Route (`backend/app/api/routes/chat.py`)

```python
# Add provider selection to WebSocket messages
from app.services.llm.factory import LLMServiceFactory, LLMProvider

@router.websocket("/ws")
async def chat_websocket(websocket: WebSocket, token: str = Query(...)):
    # ... existing auth code ...

    while True:
        data = await websocket.receive_json()

        if data.get("type") == "message":
            # Get provider from message or user preference
            provider: LLMProvider = data.get("provider", user.get("llm_provider", "claude"))

            # Get the appropriate service
            llm_service = LLMServiceFactory.get_service(provider)

            # Stream message using selected provider
            async for chunk in llm_service.stream_message(
                messages=conversation_history,
                user_phase=user_phase,
                saved_goals=goals_context,
                draft_goals=draft_goals,
                active_goal_id=active_goal_id,
            ):
                # ... existing chunk handling ...
```

### 4. Add Provider Endpoint (`backend/app/api/routes/chat.py`)

```python
@router.get("/providers")
async def get_available_providers(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get list of available LLM providers."""
    return {
        "providers": LLMServiceFactory.get_available_providers(),
        "current": current_user.get("llm_provider", "claude"),
    }

@router.put("/provider")
async def set_user_provider(
    provider: LLMProvider,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database),
):
    """Set user's preferred LLM provider."""
    available = LLMServiceFactory.get_available_providers()
    if provider not in available:
        raise HTTPException(400, f"Provider '{provider}' not available")

    await db.users.update_one(
        {"_id": current_user["_id"]},
        {"$set": {"llm_provider": provider}}
    )
    return {"provider": provider}
```

### 5. Update User Model (`backend/app/models/user.py`)

Add new field:

```python
class User(BaseModel):
    # ... existing fields ...
    llm_provider: str = "claude"  # Default to Claude
```

---

## Frontend Implementation

### 1. Update Types (`frontend/src/types/index.ts`)

```typescript
// Add LLM provider types
export type LLMProvider = 'claude' | 'openai';

export interface LLMProviderInfo {
  id: LLMProvider;
  name: string;
  description: string;
  available: boolean;
}

// Update WebSocketMessage to include provider
export interface ChatMessage {
  type: 'message';
  content: string;
  draft_goals?: DraftGoal[];
  active_goal_id?: string;
  provider?: LLMProvider;  // NEW: specify which provider to use
}

// Update User type
export interface User {
  // ... existing fields ...
  llm_provider: LLMProvider;
}
```

### 2. Create Provider Store (`frontend/src/stores/providerStore.ts`)

```typescript
import { create } from 'zustand';
import { LLMProvider, LLMProviderInfo } from '@/types';

interface ProviderState {
  currentProvider: LLMProvider;
  availableProviders: LLMProviderInfo[];
  isLoading: boolean;

  setProvider: (provider: LLMProvider) => Promise<void>;
  fetchProviders: () => Promise<void>;
}

export const useProviderStore = create<ProviderState>((set, get) => ({
  currentProvider: 'claude',
  availableProviders: [],
  isLoading: false,

  setProvider: async (provider) => {
    const response = await fetch('/api/v1/chat/provider', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider }),
    });
    if (response.ok) {
      set({ currentProvider: provider });
    }
  },

  fetchProviders: async () => {
    set({ isLoading: true });
    const response = await fetch('/api/v1/chat/providers');
    const data = await response.json();
    set({
      availableProviders: data.providers.map((p: string) => ({
        id: p,
        name: p === 'claude' ? 'Claude (Anthropic)' : 'GPT (OpenAI)',
        description: p === 'claude'
          ? 'Claude 3.5 Sonnet - Thoughtful, nuanced responses'
          : 'GPT-4o - Fast, capable responses with tracing',
        available: true,
      })),
      currentProvider: data.current,
      isLoading: false,
    });
  },
}));
```

### 3. Create Provider Selector Component (`frontend/src/components/chat/ProviderSelector.tsx`)

```typescript
import { useProviderStore } from '@/stores/providerStore';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

export function ProviderSelector() {
  const { currentProvider, availableProviders, setProvider, isLoading } = useProviderStore();

  if (availableProviders.length <= 1) {
    return null; // Don't show selector if only one provider
  }

  return (
    <Select
      value={currentProvider}
      onValueChange={(value) => setProvider(value as LLMProvider)}
      disabled={isLoading}
    >
      <SelectTrigger className="w-[180px]">
        <SelectValue placeholder="Select AI" />
      </SelectTrigger>
      <SelectContent>
        {availableProviders.map((provider) => (
          <SelectItem key={provider.id} value={provider.id}>
            <div className="flex items-center gap-2">
              {provider.id === 'claude' ? (
                <ClaudeIcon className="h-4 w-4" />
              ) : (
                <OpenAIIcon className="h-4 w-4" />
              )}
              {provider.name}
            </div>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
```

### 4. Update ChatContainer (`frontend/src/components/chat/ChatContainer.tsx`)

```typescript
import { ProviderSelector } from './ProviderSelector';
import { useProviderStore } from '@/stores/providerStore';

export function ChatContainer() {
  const { currentProvider, fetchProviders } = useProviderStore();

  useEffect(() => {
    fetchProviders();
  }, []);

  const handleSendMessage = useCallback((content: string) => {
    sendMessage({
      type: 'message',
      content,
      draft_goals: getDraftsArray(),
      active_goal_id: activeGoalId,
      provider: currentProvider,  // Include selected provider
    });
  }, [currentProvider, ...]);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-4 border-b">
        <h2>Chat with AI Coach</h2>
        <ProviderSelector />
      </div>
      {/* ... rest of chat UI */}
    </div>
  );
}
```

### 5. Update WebSocket Hook (`frontend/src/hooks/useWebSocket.ts`)

No major changes needed - the provider is passed in the message payload.

---

## Configuration & Environment

### Backend Environment Variables

Add to `.env` and `backend/app/core/config.py`:

```python
# OpenAI Configuration
OPENAI_API_KEY: Optional[str] = None
OPENAI_MODEL: str = "gpt-4o"
OPENAI_MAX_TOKENS: int = 4096
OPENAI_TEMPERATURE: float = 0.7

# Default LLM Provider (for new users)
DEFAULT_LLM_PROVIDER: str = "claude"

# Tracing Configuration
OPENAI_TRACING_ENABLED: bool = True
OPENAI_TRACING_LOG_PATH: str = "logs/openai_traces.jsonl"
```

### Update `config.py`

```python
class Settings(BaseSettings):
    # ... existing fields ...

    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_MAX_TOKENS: int = 4096
    OPENAI_TEMPERATURE: float = 0.7

    # Provider defaults
    DEFAULT_LLM_PROVIDER: str = "claude"

    # Tracing
    OPENAI_TRACING_ENABLED: bool = True
    OPENAI_TRACING_LOG_PATH: str = "logs/openai_traces.jsonl"

    def get_available_providers(self) -> List[str]:
        providers = []
        if self.ANTHROPIC_API_KEY:
            providers.append("claude")
        if self.OPENAI_API_KEY:
            providers.append("openai")
        return providers
```

---

## OpenAI Agents SDK Integration

### Installation

```bash
pip install openai-agents
```

Add to `backend/requirements.txt`:
```
openai-agents>=0.1.0
```

### Agent Architecture

The OpenAI Agents SDK provides:

1. **Agent Class**: Encapsulates model, instructions, and tools
2. **Runner Class**: Executes agent with conversation management
3. **Function Tools**: Decorated Python functions as callable tools
4. **Tracing**: Built-in observability for debugging and logging

### Tool Definition Approach

Unlike Claude's JSON schema tools, OpenAI Agents SDK uses decorated Python functions:

```python
from agents import function_tool

@function_tool
async def create_goal(
    title: str,
    content: str,
    template_type: str = "custom",
    deadline: str | None = None,
    milestones: list[dict] | None = None,
) -> dict:
    """
    Create a new goal for the user.

    Args:
        title: The goal title
        content: Detailed description in markdown
        template_type: One of 'smart', 'okr', or 'custom'
        deadline: Optional deadline in ISO format
        milestones: Optional list of milestone objects

    Returns:
        The created goal object
    """
    # Delegate to GoalToolHandler
    from app.services.goal_tool_handler import GoalToolHandler
    handler = GoalToolHandler(db, user_id)
    return await handler.execute_tool("create_goal", {
        "title": title,
        "content": content,
        "template_type": template_type,
        "deadline": deadline,
        "milestones": milestones,
    })
```

### Streaming with Agents SDK

```python
from agents import Agent, Runner

async def stream_with_agent(messages, system_prompt):
    agent = Agent(
        name="Coach",
        model="gpt-4o",
        instructions=system_prompt,
        tools=[create_goal, update_goal, set_goal_phase],
    )

    runner = Runner(agent)

    async for event in runner.run_streamed(messages=messages):
        yield event
```

---

## Tracing & Logging

### OpenAI Agents SDK Traces

The Agents SDK provides comprehensive tracing out of the box:

```python
from agents.tracing import set_tracing_export_api_key, TracingProcessor

# Configure trace export
set_tracing_export_api_key(settings.OPENAI_API_KEY)

# Custom trace processor for local logging
class GoalGetterTraceProcessor(TracingProcessor):
    def __init__(self):
        super().__init__()
        self.log_file = open(settings.OPENAI_TRACING_LOG_PATH, "a")

    def on_span_end(self, span):
        # Log to file
        trace_data = {
            "trace_id": span.trace_id,
            "span_id": span.span_id,
            "name": span.name,
            "start_time": span.start_time.isoformat(),
            "end_time": span.end_time.isoformat(),
            "duration_ms": span.duration_ms,
            "attributes": span.attributes,
            "status": span.status,
        }
        self.log_file.write(json.dumps(trace_data) + "\n")
        self.log_file.flush()

        # Also log tool calls
        if span.name.startswith("tool:"):
            logger.info(f"Tool call: {span.name}", extra=trace_data)
```

### Trace Structure

Each agent run produces traces with:

```json
{
  "trace_id": "abc123",
  "spans": [
    {
      "name": "agent_run",
      "attributes": {
        "model": "gpt-4o",
        "input_tokens": 1234,
        "output_tokens": 567
      },
      "children": [
        {
          "name": "tool:create_goal",
          "attributes": {
            "tool_input": {"title": "..."},
            "tool_output": {"id": "..."}
          }
        }
      ]
    }
  ]
}
```

### Integration with Existing Logging

Update `backend/app/core/logging.py` to include trace correlation:

```python
def configure_logging():
    # ... existing config ...

    # Add trace ID to log format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - [trace:%(trace_id)s] - %(message)s"
```

---

## Migration Strategy

### Phase 1: Infrastructure (No User Impact)

1. Create `backend/app/services/llm/` directory structure
2. Create `BaseLLMService` abstract class
3. Move and refactor `ClaudeService` to new location
4. Update imports in `chat.py`
5. Test that Claude still works exactly as before

### Phase 2: OpenAI Integration (Feature Flag)

1. Add OpenAI environment variables
2. Implement `OpenAIService` class
3. Implement `LLMServiceFactory`
4. Add provider endpoints to API
5. Test OpenAI integration with API keys

### Phase 3: Frontend UI

1. Add provider store
2. Create provider selector component
3. Integrate into chat container
4. Test provider switching

### Phase 4: Tracing & Logging

1. Configure OpenAI Agents SDK tracing
2. Add trace log file rotation
3. Add trace correlation to existing logs
4. Create trace viewer (optional)

### Phase 5: Cleanup & Documentation

1. Update API documentation
2. Add provider info to user settings page
3. Add cost tracking per provider (optional)
4. Performance comparison dashboard (optional)

---

## Testing Plan

### Unit Tests

```python
# tests/services/llm/test_base.py
def test_base_service_interface():
    """Ensure both services implement the interface correctly."""

# tests/services/llm/test_claude_service.py
def test_claude_streaming():
    """Test Claude streaming maintains existing behavior."""

def test_claude_tool_calls():
    """Test Claude tool execution."""

# tests/services/llm/test_openai_service.py
def test_openai_streaming():
    """Test OpenAI streaming."""

def test_openai_tool_calls():
    """Test OpenAI tool execution via Agents SDK."""

def test_openai_tracing():
    """Test traces are properly generated."""

# tests/services/llm/test_factory.py
def test_factory_returns_correct_service():
    """Test factory pattern."""

def test_factory_singleton_behavior():
    """Test services are cached."""
```

### Integration Tests

```python
# tests/api/test_chat_providers.py
async def test_get_providers_endpoint():
    """Test /chat/providers returns available providers."""

async def test_set_provider_endpoint():
    """Test /chat/provider updates user preference."""

async def test_websocket_with_claude():
    """Test WebSocket chat with Claude provider."""

async def test_websocket_with_openai():
    """Test WebSocket chat with OpenAI provider."""

async def test_provider_switch_mid_session():
    """Test switching providers during active session."""
```

### E2E Tests

```typescript
// frontend/e2e/provider-selection.spec.ts
test('user can switch between providers', async ({ page }) => {
  // Test provider selector appears
  // Test switching to OpenAI
  // Test message sent with correct provider
  // Test switching back to Claude
});
```

---

## File Change Summary

### New Files

| File | Description |
|------|-------------|
| `backend/app/services/llm/__init__.py` | Module exports |
| `backend/app/services/llm/base.py` | Abstract base class |
| `backend/app/services/llm/openai_service.py` | OpenAI Agents SDK implementation |
| `backend/app/services/llm/factory.py` | Service factory |
| `frontend/src/stores/providerStore.ts` | Provider state management |
| `frontend/src/components/chat/ProviderSelector.tsx` | Provider selection UI |
| `tests/services/llm/test_*.py` | Unit tests |
| `logs/openai_traces.jsonl` | Trace output (auto-created) |

### Modified Files

| File | Changes |
|------|---------|
| `backend/app/services/claude_service.py` | Move to `llm/`, implement `BaseLLMService` |
| `backend/app/api/routes/chat.py` | Add provider endpoints, update WebSocket handler |
| `backend/app/core/config.py` | Add OpenAI configuration |
| `backend/app/models/user.py` | Add `llm_provider` field |
| `backend/requirements.txt` | Add `openai-agents` |
| `frontend/src/types/index.ts` | Add provider types |
| `frontend/src/components/chat/ChatContainer.tsx` | Add provider selector, pass provider in messages |
| `frontend/src/hooks/useWebSocket.ts` | Minor updates for provider support |
| `.env.example` | Add OpenAI variables |

### Import Updates Required

After moving `claude_service.py`:

```python
# Old
from app.services.claude_service import claude_service

# New
from app.services.llm.factory import LLMServiceFactory
llm_service = LLMServiceFactory.get_service(provider)
```

---

## Dependencies

### Python

```txt
# Add to requirements.txt
openai-agents>=0.1.0
```

### Node (if icons needed)

```bash
# Optional: provider icons
npm install @anthropic-ai/icon @openai/icon
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| OpenAI API rate limits | Chat interruption | Implement retry with backoff |
| Tool schema differences | Feature disparity | Normalize in service layer |
| Trace file growth | Disk usage | Add log rotation |
| Response format differences | UI inconsistency | Normalize chunk format in services |
| Cost tracking complexity | Budget overruns | Add per-provider usage metrics |

---

## Success Criteria

1. Users can select between Claude and OpenAI in the chat UI
2. Both providers support all three goal tools (create, update, set_phase)
3. Streaming works identically for both providers
4. OpenAI traces are logged to file for debugging
5. Provider preference persists across sessions
6. No regression in Claude functionality
7. All existing tests pass
8. New tests cover provider switching

---

## Future Enhancements

1. **Cost Dashboard**: Track token usage per provider per user
2. **Auto-switching**: Fallback to alternate provider on errors
3. **Provider-specific Features**: Expose unique capabilities (e.g., Claude artifacts, GPT vision)
4. **Custom Trace Viewer**: Web UI for browsing OpenAI traces
5. **A/B Testing**: Compare response quality between providers
6. **Local LLM Support**: Add Ollama or llama.cpp as providers
