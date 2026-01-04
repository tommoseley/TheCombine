# The Combine — Interface Architecture Plan

**Status:** Draft  
**Created:** December 16, 2025  
**Purpose:** Define clean interfaces (Protocols) to improve testability, swappability, and separation of concerns.

---

## Current State

We already use `Protocol` in two places:

1. **`base_mentor.py`** — `PromptServiceProtocol`, `ArtifactServiceProtocol` for dependency injection
2. **`llm_response_parser.py`** — `ParsingStrategy` for strategy pattern

This document outlines additional opportunities to extend this pattern throughout the codebase.

---

## 1. Repository Interfaces

### Purpose
Separate data access from business logic. Enables mocking for tests and swapping storage backends.

### Location
`app/domain/interfaces/repositories.py`

```python
"""
Repository interfaces for data access abstraction.

These protocols define the contract for data persistence operations.
Implementations live in app/infrastructure/repositories/
"""

from typing import Protocol, Optional, List, Dict, Any
from datetime import datetime


class IProjectRepository(Protocol):
    """Interface for project data access."""
    
    async def get_by_id(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project by UUID."""
        ...
    
    async def get_by_project_id(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project by short ID (e.g., 'WARMPULS')."""
        ...
    
    async def list_all(
        self, 
        offset: int = 0, 
        limit: int = 20, 
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List projects with pagination and optional search."""
        ...
    
    async def create(self, name: str, description: str = "") -> Dict[str, Any]:
        """Create a new project."""
        ...
    
    async def update(self, project_id: str, **fields) -> Optional[Dict[str, Any]]:
        """Update project fields."""
        ...
    
    async def delete(self, project_id: str) -> bool:
        """Delete a project. Returns True if deleted."""
        ...


class IEpicRepository(Protocol):
    """Interface for epic data access."""
    
    async def get_by_id(self, epic_id: str) -> Optional[Dict[str, Any]]:
        """Get epic by UUID."""
        ...
    
    async def get_by_epic_id(self, epic_id: str) -> Optional[Dict[str, Any]]:
        """Get epic by short ID (e.g., 'WARM-001')."""
        ...
    
    async def list_by_project(self, project_id: str) -> List[Dict[str, Any]]:
        """List all epics for a project."""
        ...
    
    async def create(
        self, 
        project_id: str, 
        epic_id: str,
        title: str, 
        description: str = ""
    ) -> Dict[str, Any]:
        """Create a new epic."""
        ...
    
    async def update(self, epic_id: str, **fields) -> Optional[Dict[str, Any]]:
        """Update epic fields."""
        ...


class IArtifactRepository(Protocol):
    """Interface for artifact data access."""
    
    async def get_by_id(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        """Get artifact by UUID."""
        ...
    
    async def get_by_path(self, artifact_path: str) -> Optional[Dict[str, Any]]:
        """Get artifact by path (e.g., 'WARMPULS/ARCH/DISCOVERY')."""
        ...
    
    async def list_by_project(self, project_id: str) -> List[Dict[str, Any]]:
        """List all artifacts for a project."""
        ...
    
    async def list_by_epic(self, epic_id: str) -> List[Dict[str, Any]]:
        """List all artifacts for an epic."""
        ...
    
    async def create(
        self,
        artifact_path: str,
        artifact_type: str,
        title: str,
        content: Dict[str, Any],
        breadcrumbs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new artifact."""
        ...
    
    async def update_content(
        self, 
        artifact_id: str, 
        content: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update artifact content."""
        ...


class IPromptRepository(Protocol):
    """Interface for prompt template data access."""
    
    async def get_by_id(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        """Get prompt by ID."""
        ...
    
    async def get_active_prompt(
        self, 
        role_name: str, 
        pipeline_id: str, 
        phase: str
    ) -> Optional[Dict[str, Any]]:
        """Get the active prompt for a role/pipeline/phase combination."""
        ...
    
    async def create(
        self,
        role_name: str,
        pipeline_id: str,
        phase: str,
        template: str,
        version: str = "1.0"
    ) -> Dict[str, Any]:
        """Create a new prompt template."""
        ...
```

### Implementation Example

```python
# app/infrastructure/repositories/sqlalchemy_project_repository.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.models import Project
from app.domain.interfaces.repositories import IProjectRepository


class SQLAlchemyProjectRepository:
    """SQLAlchemy implementation of IProjectRepository."""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def get_by_id(self, project_id: str) -> Optional[Dict[str, Any]]:
        query = select(Project).where(Project.id == project_id)
        result = await self._session.execute(query)
        project = result.scalar_one_or_none()
        return self._to_dict(project) if project else None
    
    async def list_all(
        self, 
        offset: int = 0, 
        limit: int = 20, 
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        query = select(Project).offset(offset).limit(limit)
        if search:
            query = query.where(Project.name.ilike(f"%{search}%"))
        result = await self._session.execute(query)
        return [self._to_dict(p) for p in result.scalars().all()]
    
    def _to_dict(self, project: Project) -> Dict[str, Any]:
        return {
            "id": str(project.id),
            "project_id": project.project_id,
            "name": project.name,
            "description": project.description,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
        }
```

### Mock Example for Testing

```python
# tests/mocks/mock_repositories.py

class MockProjectRepository:
    """In-memory mock for testing."""
    
    def __init__(self):
        self._projects: Dict[str, Dict[str, Any]] = {}
    
    async def get_by_id(self, project_id: str) -> Optional[Dict[str, Any]]:
        return self._projects.get(project_id)
    
    async def create(self, name: str, description: str = "") -> Dict[str, Any]:
        project_id = f"TEST-{len(self._projects) + 1}"
        project = {
            "id": str(uuid4()),
            "project_id": project_id,
            "name": name,
            "description": description,
        }
        self._projects[project["id"]] = project
        return project
```

---

## 2. LLM Client Interface

### Purpose
Abstract the LLM provider (Anthropic, OpenAI, local models). Enables testing without API calls and provider flexibility.

### Location
`app/domain/interfaces/llm.py`

```python
"""
LLM client interfaces for AI model abstraction.

These protocols define the contract for LLM interactions.
Implementations live in app/infrastructure/llm/
"""

from typing import Protocol, AsyncGenerator, Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class LLMMessage:
    """A single message in a conversation."""
    role: str  # "user", "assistant", "system"
    content: str


@dataclass
class LLMResponse:
    """Response from an LLM call."""
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    stop_reason: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None


@dataclass
class LLMStreamChunk:
    """A single chunk from a streaming response."""
    content: str
    is_final: bool = False
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None


class ILLMClient(Protocol):
    """Interface for LLM client operations."""
    
    async def complete(
        self,
        messages: List[LLMMessage],
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """
        Send a completion request and wait for full response.
        
        Args:
            messages: Conversation history
            system: System prompt
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            
        Returns:
            Complete LLM response
        """
        ...
    
    async def stream(
        self,
        messages: List[LLMMessage],
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """
        Send a completion request and stream the response.
        
        Args:
            messages: Conversation history
            system: System prompt
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            
        Yields:
            Stream chunks as they arrive
        """
        ...
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        ...


class ILLMClientFactory(Protocol):
    """Factory for creating LLM clients."""
    
    def create(self, model: str) -> ILLMClient:
        """Create a client for the specified model."""
        ...
```

### Implementation Example

```python
# app/infrastructure/llm/anthropic_client.py

from anthropic import Anthropic
from app.domain.interfaces.llm import ILLMClient, LLMMessage, LLMResponse, LLMStreamChunk


class AnthropicClient:
    """Anthropic Claude implementation of ILLMClient."""
    
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self._client = Anthropic(api_key=api_key)
        self._model = model
    
    async def complete(
        self,
        messages: List[LLMMessage],
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=temperature,
            **kwargs
        )
        
        return LLMResponse(
            content=response.content[0].text,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            stop_reason=response.stop_reason,
            raw_response=response.model_dump(),
        )
    
    async def stream(
        self,
        messages: List[LLMMessage],
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        with self._client.messages.stream(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=temperature,
            **kwargs
        ) as stream:
            for text in stream.text_stream:
                yield LLMStreamChunk(content=text)
            
            # Final chunk with usage info
            final = stream.get_final_message()
            yield LLMStreamChunk(
                content="",
                is_final=True,
                input_tokens=final.usage.input_tokens,
                output_tokens=final.usage.output_tokens,
            )
```

### Mock Example for Testing

```python
# tests/mocks/mock_llm.py

class MockLLMClient:
    """Mock LLM for testing without API calls."""
    
    def __init__(self, responses: Optional[List[str]] = None):
        self._responses = responses or ["Mock LLM response"]
        self._call_index = 0
        self.calls: List[Dict[str, Any]] = []  # Record calls for assertions
    
    async def complete(
        self,
        messages: List[LLMMessage],
        system: str = "",
        **kwargs
    ) -> LLMResponse:
        self.calls.append({"messages": messages, "system": system, **kwargs})
        response = self._responses[self._call_index % len(self._responses)]
        self._call_index += 1
        
        return LLMResponse(
            content=response,
            model="mock-model",
            input_tokens=100,
            output_tokens=50,
        )
    
    async def stream(self, messages: List[LLMMessage], **kwargs):
        response = await self.complete(messages, **kwargs)
        words = response.content.split()
        for word in words:
            yield LLMStreamChunk(content=word + " ")
        yield LLMStreamChunk(content="", is_final=True, input_tokens=100, output_tokens=50)
```

---

## 3. Mentor Interface

### Purpose
Formalize the contract all mentors must implement. Ensures consistency and enables generic mentor orchestration.

### Location
`app/domain/interfaces/mentors.py`

```python
"""
Mentor interfaces for AI-guided workflow steps.

These protocols define the contract for mentor implementations.
"""

from typing import Protocol, AsyncGenerator, Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class MentorRole(str, Enum):
    """Available mentor roles."""
    PM = "pm"
    BA = "ba"
    ARCHITECT = "architect"
    DEVELOPER = "developer"
    QA = "qa"


@dataclass
class MentorContext:
    """Input context for a mentor execution."""
    project_id: str
    epic_id: Optional[str] = None
    artifact_path: Optional[str] = None
    user_input: Optional[str] = None
    previous_artifacts: Optional[List[Dict[str, Any]]] = None
    options: Optional[Dict[str, Any]] = None


@dataclass
class MentorResult:
    """Result of a mentor execution."""
    success: bool
    artifact: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    tokens_used: int = 0
    cost_usd: float = 0.0
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ProgressUpdate:
    """Progress update during mentor execution."""
    step: str
    message: str
    progress_percent: int
    icon: str = "loader"
    status: str = "running"  # running, complete, error


class IMentor(Protocol):
    """Interface for all mentors."""
    
    @property
    def role(self) -> MentorRole:
        """The role this mentor plays."""
        ...
    
    @property
    def description(self) -> str:
        """Human-readable description of what this mentor does."""
        ...
    
    async def execute(self, context: MentorContext) -> MentorResult:
        """
        Execute the mentor's workflow synchronously.
        
        Args:
            context: Input context with project/epic info
            
        Returns:
            Result with artifact and metadata
        """
        ...
    
    async def execute_stream(
        self, 
        context: MentorContext
    ) -> AsyncGenerator[ProgressUpdate, MentorResult]:
        """
        Execute the mentor's workflow with streaming progress.
        
        Args:
            context: Input context with project/epic info
            
        Yields:
            Progress updates during execution
            
        Returns:
            Final result with artifact and metadata
        """
        ...
    
    def get_progress_steps(self) -> List[ProgressUpdate]:
        """Get the list of progress steps this mentor will go through."""
        ...
    
    async def validate_context(self, context: MentorContext) -> tuple[bool, Optional[str]]:
        """
        Validate that the context is sufficient for execution.
        
        Returns:
            (is_valid, error_message)
        """
        ...


class IMentorFactory(Protocol):
    """Factory for creating mentors."""
    
    def create(self, role: MentorRole) -> IMentor:
        """Create a mentor for the specified role."""
        ...
    
    def list_available(self) -> List[MentorRole]:
        """List available mentor roles."""
        ...
```

### Usage Example

```python
# app/domain/services/mentor_orchestrator.py

class MentorOrchestrator:
    """Orchestrates mentor execution across a workflow."""
    
    def __init__(self, mentor_factory: IMentorFactory):
        self._factory = mentor_factory
    
    async def run_pipeline(
        self, 
        roles: List[MentorRole], 
        context: MentorContext
    ) -> List[MentorResult]:
        """Run a sequence of mentors."""
        results = []
        
        for role in roles:
            mentor = self._factory.create(role)
            
            # Validate before running
            is_valid, error = await mentor.validate_context(context)
            if not is_valid:
                results.append(MentorResult(success=False, error_message=error))
                break
            
            # Execute
            result = await mentor.execute(context)
            results.append(result)
            
            # Feed output to next mentor
            if result.artifact:
                context.previous_artifacts = context.previous_artifacts or []
                context.previous_artifacts.append(result.artifact)
        
        return results
```

---

## 4. Event System Interface

### Purpose
Decouple "something happened" from "what to do about it". Enables audit logging, notifications, analytics, etc. without cluttering business logic.

### Location
`app/domain/interfaces/events.py`

```python
"""
Event system interfaces for domain event handling.

These protocols enable loose coupling between components through events.
"""

from typing import Protocol, Dict, Any, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class EventType(str, Enum):
    """Domain event types."""
    # Project events
    PROJECT_CREATED = "project.created"
    PROJECT_UPDATED = "project.updated"
    PROJECT_DELETED = "project.deleted"
    
    # Epic events
    EPIC_CREATED = "epic.created"
    EPIC_UPDATED = "epic.updated"
    EPIC_STATUS_CHANGED = "epic.status_changed"
    
    # Artifact events
    ARTIFACT_CREATED = "artifact.created"
    ARTIFACT_UPDATED = "artifact.updated"
    
    # Mentor events
    MENTOR_STARTED = "mentor.started"
    MENTOR_PROGRESS = "mentor.progress"
    MENTOR_COMPLETED = "mentor.completed"
    MENTOR_FAILED = "mentor.failed"
    
    # Pipeline events
    PIPELINE_STARTED = "pipeline.started"
    PIPELINE_STAGE_COMPLETED = "pipeline.stage_completed"
    PIPELINE_COMPLETED = "pipeline.completed"
    PIPELINE_FAILED = "pipeline.failed"


@dataclass
class DomainEvent:
    """Base class for all domain events."""
    event_type: EventType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = None  # For tracing related events
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


# Type alias for event handlers
EventHandler = Callable[[DomainEvent], Awaitable[None]]


class IEventPublisher(Protocol):
    """Interface for publishing domain events."""
    
    async def publish(self, event: DomainEvent) -> None:
        """
        Publish an event to all registered handlers.
        
        Args:
            event: The domain event to publish
        """
        ...
    
    async def publish_many(self, events: List[DomainEvent]) -> None:
        """
        Publish multiple events.
        
        Args:
            events: List of events to publish
        """
        ...


class IEventSubscriber(Protocol):
    """Interface for subscribing to domain events."""
    
    def subscribe(
        self, 
        event_type: EventType, 
        handler: EventHandler
    ) -> Callable[[], None]:
        """
        Subscribe to an event type.
        
        Args:
            event_type: The type of event to listen for
            handler: Async function to call when event occurs
            
        Returns:
            Unsubscribe function
        """
        ...
    
    def subscribe_all(self, handler: EventHandler) -> Callable[[], None]:
        """
        Subscribe to all events.
        
        Args:
            handler: Async function to call for any event
            
        Returns:
            Unsubscribe function
        """
        ...


class IEventStore(Protocol):
    """Interface for persisting events (event sourcing support)."""
    
    async def append(self, event: DomainEvent) -> None:
        """Append an event to the store."""
        ...
    
    async def get_events(
        self,
        aggregate_id: Optional[str] = None,
        event_types: Optional[List[EventType]] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[DomainEvent]:
        """Query events from the store."""
        ...
```

### Implementation Example

```python
# app/infrastructure/events/in_memory_event_bus.py

from collections import defaultdict
from typing import Dict, List, Callable
from app.domain.interfaces.events import (
    IEventPublisher, IEventSubscriber, DomainEvent, EventType, EventHandler
)


class InMemoryEventBus(IEventPublisher, IEventSubscriber):
    """Simple in-memory event bus implementation."""
    
    def __init__(self):
        self._handlers: Dict[EventType, List[EventHandler]] = defaultdict(list)
        self._global_handlers: List[EventHandler] = []
    
    async def publish(self, event: DomainEvent) -> None:
        # Call specific handlers
        for handler in self._handlers[event.event_type]:
            await handler(event)
        
        # Call global handlers
        for handler in self._global_handlers:
            await handler(event)
    
    async def publish_many(self, events: List[DomainEvent]) -> None:
        for event in events:
            await self.publish(event)
    
    def subscribe(
        self, 
        event_type: EventType, 
        handler: EventHandler
    ) -> Callable[[], None]:
        self._handlers[event_type].append(handler)
        
        def unsubscribe():
            self._handlers[event_type].remove(handler)
        
        return unsubscribe
    
    def subscribe_all(self, handler: EventHandler) -> Callable[[], None]:
        self._global_handlers.append(handler)
        
        def unsubscribe():
            self._global_handlers.remove(handler)
        
        return unsubscribe
```

### Usage Example

```python
# app/domain/services/audit_service.py

class AuditService:
    """Logs all domain events for audit trail."""
    
    def __init__(self, event_subscriber: IEventSubscriber, logger: logging.Logger):
        self._logger = logger
        # Subscribe to all events
        event_subscriber.subscribe_all(self._handle_event)
    
    async def _handle_event(self, event: DomainEvent) -> None:
        self._logger.info(
            f"AUDIT: {event.event_type.value}",
            extra={
                "event_id": event.event_id,
                "correlation_id": event.correlation_id,
                "payload": event.payload,
                "timestamp": event.timestamp.isoformat(),
            }
        )


# In mentor execution:
async def execute(self, context: MentorContext) -> MentorResult:
    await self._event_publisher.publish(DomainEvent(
        event_type=EventType.MENTOR_STARTED,
        payload={"role": self.role.value, "project_id": context.project_id}
    ))
    
    try:
        result = await self._do_work(context)
        
        await self._event_publisher.publish(DomainEvent(
            event_type=EventType.MENTOR_COMPLETED,
            payload={"role": self.role.value, "artifact_id": result.artifact["id"]}
        ))
        
        return result
    except Exception as e:
        await self._event_publisher.publish(DomainEvent(
            event_type=EventType.MENTOR_FAILED,
            payload={"role": self.role.value, "error": str(e)}
        ))
        raise
```

---

## 5. ID Generation Interface

### Purpose
Abstract ID generation strategy. Currently in `base_mentor.py` as `IdGeneratorFunc`. Formalize it.

### Location
`app/domain/interfaces/id_generation.py`

```python
"""
ID generation interfaces.

Abstracts how entity IDs are generated (sequential, UUID, custom format).
"""

from typing import Protocol, Optional


class IIdGenerator(Protocol):
    """Interface for generating entity IDs."""
    
    async def generate_project_id(self, name: str) -> str:
        """
        Generate a project ID from name.
        
        Example: "Warm Pulse System" -> "WARMPULS"
        """
        ...
    
    async def generate_epic_id(self, project_id: str, sequence: Optional[int] = None) -> str:
        """
        Generate an epic ID for a project.
        
        Example: project_id="WARMPULS", sequence=1 -> "WARM-001"
        """
        ...
    
    async def generate_story_id(self, epic_id: str, sequence: Optional[int] = None) -> str:
        """
        Generate a story ID for an epic.
        
        Example: epic_id="WARM-001", sequence=5 -> "WARM-001-005"
        """
        ...
    
    async def generate_artifact_path(
        self,
        project_id: str,
        artifact_type: str,
        sub_type: Optional[str] = None,
        epic_id: Optional[str] = None
    ) -> str:
        """
        Generate an artifact path.
        
        Examples:
            - "WARMPULS/ARCH/DISCOVERY"
            - "WARMPULS/EPIC/WARM-001/STORIES"
        """
        ...
```

---

## 6. Configuration Interface

### Purpose
Abstract configuration sources. Enables env vars, files, remote config, feature flags.

### Location
`app/domain/interfaces/config.py`

```python
"""
Configuration interfaces.

Abstracts configuration sources for flexibility and testing.
"""

from typing import Protocol, Optional, Any, Dict


class IConfigProvider(Protocol):
    """Interface for configuration access."""
    
    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """Get a configuration value."""
        ...
    
    def get_string(self, key: str, default: str = "") -> str:
        """Get a string configuration value."""
        ...
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Get an integer configuration value."""
        ...
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a boolean configuration value."""
        ...
    
    def get_section(self, prefix: str) -> Dict[str, Any]:
        """Get all config values with a prefix."""
        ...


class IFeatureFlags(Protocol):
    """Interface for feature flag access."""
    
    def is_enabled(self, flag: str, default: bool = False) -> bool:
        """Check if a feature flag is enabled."""
        ...
    
    def get_variant(self, flag: str, default: str = "control") -> str:
        """Get the variant for an A/B test flag."""
        ...
```

---

## Implementation Priority

### Phase 1: High Impact (This Week)
1. **`IProjectRepository`** — Most used, high test value
2. **`ILLMClient`** — Enables testing without API costs
3. **`IArtifactRepository`** — Core to the system

### Phase 2: Clean Architecture (Next Week)
4. **`IMentor`** — Formalize mentor contract
5. **`IEpicRepository`** — Complete repository layer
6. **`IIdGenerator`** — Already partially exists

### Phase 3: Advanced Patterns (Future)
7. **Event System** — When audit/notifications needed
8. **`IConfigProvider`** — When config complexity grows
9. **`IFeatureFlags`** — When A/B testing needed

---

## Folder Structure

```
app/
├── domain/
│   ├── interfaces/           # All Protocol definitions
│   │   ├── __init__.py
│   │   ├── repositories.py   # IProjectRepository, IArtifactRepository, etc.
│   │   ├── llm.py            # ILLMClient, ILLMClientFactory
│   │   ├── mentors.py        # IMentor, IMentorFactory
│   │   ├── events.py         # IEventPublisher, IEventSubscriber
│   │   ├── id_generation.py  # IIdGenerator
│   │   └── config.py         # IConfigProvider, IFeatureFlags
│   ├── services/             # Business logic (uses interfaces)
│   └── mentors/              # Mentor implementations
├── infrastructure/           # Concrete implementations
│   ├── repositories/
│   │   ├── sqlalchemy_project_repo.py
│   │   └── sqlalchemy_artifact_repo.py
│   ├── llm/
│   │   ├── anthropic_client.py
│   │   └── openai_client.py
│   └── events/
│       └── in_memory_event_bus.py
└── tests/
    └── mocks/                # Mock implementations for testing
        ├── mock_repositories.py
        ├── mock_llm.py
        └── mock_events.py
```

---

## Benefits Summary

| Interface | Testability | Swappability | Separation |
|-----------|-------------|--------------|------------|
| Repository | Mock DB, no I/O in tests | SQL → NoSQL, file-based | Business logic ≠ persistence |
| LLM Client | No API calls in tests | Anthropic → OpenAI → local | Mentor logic ≠ LLM specifics |
| Mentor | Test orchestration | Swap implementations | Contract is explicit |
| Events | Verify events published | Log → Queue → Webhook | Side effects decoupled |
| Config | Override for tests | Env → File → Remote | App ≠ environment |

---

*Clean interfaces make clean code. Implement incrementally.*
