"""State persistence - save and restore workflow state.

Provides file-based persistence for development/testing.
Production implementations may use database storage.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Protocol, Tuple

from app.domain.workflow.context import WorkflowContext
from app.domain.workflow.models import Workflow
from app.domain.workflow.workflow_state import WorkflowState


logger = logging.getLogger(__name__)


class StatePersistence(Protocol):
    """Protocol for state persistence."""
    
    async def save(
        self,
        state: WorkflowState,
        context: WorkflowContext,
    ) -> None:
        """Save current state and context."""
        ...
    
    async def load(
        self,
        workflow_id: str,
        project_id: str,
        workflow: Workflow,
    ) -> Optional[Tuple[WorkflowState, WorkflowContext]]:
        """Load saved state and context."""
        ...
    
    async def delete(
        self,
        workflow_id: str,
        project_id: str,
    ) -> None:
        """Delete saved state."""
        ...
    
    async def exists(
        self,
        workflow_id: str,
        project_id: str,
    ) -> bool:
        """Check if saved state exists."""
        ...


class FileStatePersistence:
    """File-based state persistence for development/testing."""
    
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_state_path(self, workflow_id: str, project_id: str) -> Path:
        """Get path for state file."""
        return self.base_dir / f"{workflow_id}_{project_id}_state.json"
    
    def _get_context_path(self, workflow_id: str, project_id: str) -> Path:
        """Get path for context file."""
        return self.base_dir / f"{workflow_id}_{project_id}_context.json"
    
    async def save(
        self,
        state: WorkflowState,
        context: WorkflowContext,
    ) -> None:
        """Save current state and context to files."""
        state_path = self._get_state_path(state.workflow_id, state.project_id)
        context_path = self._get_context_path(state.workflow_id, state.project_id)
        
        # Save state
        state_data = state.to_dict()
        with open(state_path, 'w', encoding='utf-8') as f:
            json.dump(state_data, f, indent=2)
        
        # Save context
        context_data = context.to_dict()
        with open(context_path, 'w', encoding='utf-8') as f:
            json.dump(context_data, f, indent=2)
        
        logger.info(f"Saved state for {state.workflow_id}/{state.project_id}")
    
    async def load(
        self,
        workflow_id: str,
        project_id: str,
        workflow: Workflow,
    ) -> Optional[Tuple[WorkflowState, WorkflowContext]]:
        """Load saved state and context from files."""
        state_path = self._get_state_path(workflow_id, project_id)
        context_path = self._get_context_path(workflow_id, project_id)
        
        if not state_path.exists() or not context_path.exists():
            return None
        
        try:
            with open(state_path, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
            state = WorkflowState.from_dict(state_data)
            
            with open(context_path, 'r', encoding='utf-8') as f:
                context_data = json.load(f)
            context = WorkflowContext.from_dict(context_data, workflow)
            
            logger.info(f"Loaded state for {workflow_id}/{project_id}")
            return (state, context)
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to load state: {e}")
            return None
    
    async def delete(
        self,
        workflow_id: str,
        project_id: str,
    ) -> None:
        """Delete saved state files."""
        state_path = self._get_state_path(workflow_id, project_id)
        context_path = self._get_context_path(workflow_id, project_id)
        
        if state_path.exists():
            state_path.unlink()
        if context_path.exists():
            context_path.unlink()
        
        logger.info(f"Deleted state for {workflow_id}/{project_id}")
    
    async def exists(
        self,
        workflow_id: str,
        project_id: str,
    ) -> bool:
        """Check if saved state exists."""
        state_path = self._get_state_path(workflow_id, project_id)
        return state_path.exists()
    
    async def list_all(self) -> list:
        """List all saved workflow states."""
        results = []
        for path in self.base_dir.glob("*_state.json"):
            parts = path.stem.rsplit("_state", 1)[0].split("_", 1)
            if len(parts) == 2:
                results.append({"workflow_id": parts[0], "project_id": parts[1]})
        return results


class InMemoryStatePersistence:
    """In-memory state persistence for testing."""
    
    def __init__(self):
        self._states: dict = {}
        self._contexts: dict = {}
    
    def _make_key(self, workflow_id: str, project_id: str) -> str:
        return f"{workflow_id}:{project_id}"
    
    async def save(
        self,
        state: WorkflowState,
        context: WorkflowContext,
    ) -> None:
        key = self._make_key(state.workflow_id, state.project_id)
        self._states[key] = state.to_dict()
        self._contexts[key] = context.to_dict()
    
    async def load(
        self,
        workflow_id: str,
        project_id: str,
        workflow: Workflow,
    ) -> Optional[Tuple[WorkflowState, WorkflowContext]]:
        key = self._make_key(workflow_id, project_id)
        if key not in self._states:
            return None
        state = WorkflowState.from_dict(self._states[key])
        context = WorkflowContext.from_dict(self._contexts[key], workflow)
        return (state, context)
    
    async def delete(
        self,
        workflow_id: str,
        project_id: str,
    ) -> None:
        key = self._make_key(workflow_id, project_id)
        self._states.pop(key, None)
        self._contexts.pop(key, None)
    
    async def exists(
        self,
        workflow_id: str,
        project_id: str,
    ) -> bool:
        key = self._make_key(workflow_id, project_id)
        return key in self._states
