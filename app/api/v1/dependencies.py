"""FastAPI dependency injection for API endpoints."""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from app.domain.workflow import (
    WorkflowRegistry,
    WorkflowLoader,
    PromptLoader,
    FileStatePersistence,
    InMemoryStatePersistence,
    StatePersistence,
)


class Settings(BaseModel):
    """Application settings."""
    
    workflow_dir: Path = Path("seed/workflows")
    prompt_dir: Path = Path("seed/prompts")
    state_dir: Path = Path("data/workflow_state")
    use_memory_persistence: bool = False
    
    model_config = {"arbitrary_types_allowed": True}


@lru_cache
def get_settings() -> Settings:
    """Get application settings (cached)."""
    return Settings()


class User(BaseModel):
    """Stub user model for auth."""
    
    user_id: str
    email: str
    roles: list[str] = []


def get_current_user() -> User:
    """Get authenticated user (stub for Phase 3).
    
    Returns a mock user. Full authentication in Phase 4.
    """
    return User(
        user_id="user_stub",
        email="stub@example.com",
        roles=["user"],
    )


@lru_cache
def get_workflow_registry() -> WorkflowRegistry:
    """Get workflow registry with loaded definitions."""
    settings = get_settings()
    return WorkflowRegistry(workflows_dir=settings.workflow_dir)


@lru_cache
def get_prompt_loader() -> PromptLoader:
    """Get prompt loader for role/task prompts."""
    settings = get_settings()
    return PromptLoader(base_path=settings.prompt_dir)


def get_persistence() -> StatePersistence:
    """Get state persistence implementation."""
    settings = get_settings()
    if settings.use_memory_persistence:
        return InMemoryStatePersistence()
    settings.state_dir.mkdir(parents=True, exist_ok=True)
    return FileStatePersistence(settings.state_dir)


def clear_caches() -> None:
    """Clear cached dependencies (for testing)."""
    get_settings.cache_clear()
    get_workflow_registry.cache_clear()
    get_prompt_loader.cache_clear()
