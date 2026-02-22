"""Workflow registry - in-memory cache of loaded workflows.

Provides singleton-like access to available workflows.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

from app.domain.workflow.loader import WorkflowLoader, WorkflowLoadError
from app.domain.workflow.models import Workflow


logger = logging.getLogger(__name__)


class WorkflowNotFoundError(Exception):
    """Raised when requested workflow doesn't exist."""
    pass


class WorkflowRegistry:
    """In-memory registry of available workflows.

    Loads all workflows from a directory on initialization.
    Provides lookup by workflow_id.

    Supports two structures:
    1. Flat: directory/*.json (legacy flat structure)
    2. Versioned: directory/{workflow_id}/releases/{version}/definition.json
       Uses _active/active_releases.json for version resolution.

    Usage:
        registry = WorkflowRegistry(Path("combine-config/workflows"))
        workflow = registry.get("software_product_development")

        # Or list all available
        for wf_id in registry.list_ids():
            print(wf_id)
    """

    def __init__(
        self,
        workflows_dir: Optional[Path] = None,
        loader: Optional[WorkflowLoader] = None,
    ):
        """Initialize registry.

        Args:
            workflows_dir: Directory containing workflow JSON files.
                          Defaults to combine-config/workflows
            loader: Custom loader instance. Defaults to new WorkflowLoader.
        """
        self._workflows: Dict[str, Workflow] = {}
        self._loader = loader or WorkflowLoader()
        self._workflows_dir = workflows_dir or Path("combine-config/workflows")

        self._load_all()

    def _load_active_releases(self) -> Optional[Dict[str, Any]]:
        """Load active_releases.json from combine-config structure.

        Returns:
            Parsed active_releases dict or None if not found
        """
        # active_releases.json is at combine-config/_active/active_releases.json
        # If directory is combine-config/workflows, look in parent/_active/
        active_path = self._workflows_dir.parent / "_active" / "active_releases.json"
        if active_path.exists():
            try:
                with open(active_path, "r", encoding="utf-8-sig") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load active_releases.json: {e}")
        return None

    def _load_all(self) -> None:
        """Load all workflows from the workflows directory.

        Supports both flat and versioned structures.
        """
        if not self._workflows_dir.exists():
            logger.warning(f"Workflows directory not found: {self._workflows_dir}")
            return

        # Check for versioned structure (combine-config style)
        active_releases = self._load_active_releases()
        if active_releases:
            # Load from versioned structure
            for workflow_id, version in active_releases.get("workflows", {}).items():
                definition_path = self._workflows_dir / workflow_id / "releases" / version / "definition.json"
                if definition_path.exists():
                    try:
                        workflow = self._loader.load(definition_path)
                        self._workflows[workflow.workflow_id] = workflow
                        logger.info(f"Loaded workflow: {workflow.workflow_id} v{version}")
                    except WorkflowLoadError as e:
                        logger.warning(f"Failed to load workflow {workflow_id}: {e}")
                else:
                    logger.warning(f"Workflow definition not found: {definition_path}")
        else:
            # Fall back to flat structure (legacy)
            for path in self._workflows_dir.glob("*.json"):
                try:
                    workflow = self._loader.load(path)
                    self._workflows[workflow.workflow_id] = workflow
                    logger.info(f"Loaded workflow: {workflow.workflow_id} ({workflow.name})")
                except WorkflowLoadError as e:
                    logger.error(f"Failed to load workflow {path}: {e}")
                # Continue loading others
    
    def get(self, workflow_id: str) -> Workflow:
        """Get workflow by ID.
        
        Args:
            workflow_id: The workflow_id from the workflow definition
            
        Returns:
            The loaded Workflow
            
        Raises:
            WorkflowNotFoundError: If workflow not in registry
        """
        if workflow_id not in self._workflows:
            available = ", ".join(self._workflows.keys()) or "(none)"
            raise WorkflowNotFoundError(
                f"Workflow '{workflow_id}' not found. Available: {available}"
            )
        return self._workflows[workflow_id]
    
    def get_optional(self, workflow_id: str) -> Optional[Workflow]:
        """Get workflow by ID, returning None if not found."""
        return self._workflows.get(workflow_id)
    
    def list_ids(self) -> List[str]:
        """List all available workflow IDs."""
        return list(self._workflows.keys())
    
    def list_all(self) -> List[Workflow]:
        """Get all loaded workflows."""
        return list(self._workflows.values())
    
    def count(self) -> int:
        """Return number of loaded workflows."""
        return len(self._workflows)
    
    def reload(self) -> None:
        """Reload all workflows from disk."""
        self._workflows.clear()
        self._load_all()
    
    def add(self, workflow: Workflow) -> None:
        """Add a workflow to the registry.
        
        Useful for testing or dynamic workflow creation.
        """
        self._workflows[workflow.workflow_id] = workflow
    
    def remove(self, workflow_id: str) -> bool:
        """Remove a workflow from the registry.
        
        Returns True if removed, False if not found.
        """
        if workflow_id in self._workflows:
            del self._workflows[workflow_id]
            return True
        return False