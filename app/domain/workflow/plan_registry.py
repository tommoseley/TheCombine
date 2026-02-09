"""Registry for Document Interaction Workflow Plans (ADR-039).

Provides cached access to loaded workflow plans.
"""

from pathlib import Path
from typing import Dict, List, Optional

from app.domain.workflow.plan_loader import PlanLoader, PlanLoadError
from app.domain.workflow.plan_models import WorkflowPlan


class PlanNotFoundError(Exception):
    """Raised when a requested plan is not found."""

    def __init__(self, plan_id: str, available: Optional[List[str]] = None):
        self.plan_id = plan_id
        self.available = available or []
        msg = f"Workflow plan not found: {plan_id}"
        if self.available:
            msg += f". Available plans: {', '.join(self.available)}"
        super().__init__(msg)


class PlanRegistry:
    """Registry for workflow plans with caching.

    Usage:
        registry = PlanRegistry()
        registry.load_from_directory(Path("combine-config/workflows"))
        plan = registry.get("concierge_intake")
    """

    def __init__(self, loader: Optional[PlanLoader] = None):
        """Initialize registry with optional custom loader."""
        self.loader = loader or PlanLoader()
        self._plans: Dict[str, WorkflowPlan] = {}
        self._plans_by_document_type: Dict[str, WorkflowPlan] = {}

    def register(self, plan: WorkflowPlan) -> None:
        """Register a workflow plan.

        Args:
            plan: The workflow plan to register

        Raises:
            ValueError: If a plan with the same ID is already registered
        """
        if plan.workflow_id in self._plans:
            raise ValueError(
                f"Plan already registered: {plan.workflow_id}. "
                "Use replace() to update."
            )
        self._plans[plan.workflow_id] = plan
        if plan.document_type:
            self._plans_by_document_type[plan.document_type] = plan

    def replace(self, plan: WorkflowPlan) -> None:
        """Replace an existing workflow plan (or register if new).

        Args:
            plan: The workflow plan to register/replace
        """
        # Remove old document_type mapping if it exists
        if plan.workflow_id in self._plans:
            old_plan = self._plans[plan.workflow_id]
            if old_plan.document_type in self._plans_by_document_type:
                del self._plans_by_document_type[old_plan.document_type]

        self._plans[plan.workflow_id] = plan
        if plan.document_type:
            self._plans_by_document_type[plan.document_type] = plan

    def get(self, plan_id: str) -> WorkflowPlan:
        """Get a workflow plan by ID.

        Args:
            plan_id: The workflow_id of the plan

        Returns:
            The WorkflowPlan

        Raises:
            PlanNotFoundError: If plan not found
        """
        if plan_id not in self._plans:
            raise PlanNotFoundError(plan_id, available=list(self._plans.keys()))
        return self._plans[plan_id]

    def get_by_document_type(self, document_type: str) -> Optional[WorkflowPlan]:
        """Get a workflow plan by document type.

        Args:
            document_type: The document type the plan produces

        Returns:
            The WorkflowPlan or None if not found
        """
        return self._plans_by_document_type.get(document_type)

    def get_optional(self, plan_id: str) -> Optional[WorkflowPlan]:
        """Get a workflow plan by ID, returning None if not found.

        Args:
            plan_id: The workflow_id of the plan

        Returns:
            The WorkflowPlan or None
        """
        return self._plans.get(plan_id)

    def list_ids(self) -> List[str]:
        """List all registered plan IDs.

        Returns:
            List of workflow_id values
        """
        return list(self._plans.keys())

    def list_plans(self) -> List[WorkflowPlan]:
        """List all registered plans.

        Returns:
            List of WorkflowPlan objects
        """
        return list(self._plans.values())

    def has(self, plan_id: str) -> bool:
        """Check if a plan is registered.

        Args:
            plan_id: The workflow_id to check

        Returns:
            True if registered
        """
        return plan_id in self._plans

    def clear(self) -> None:
        """Clear all registered plans."""
        self._plans.clear()
        self._plans_by_document_type.clear()

    def load_from_directory(self, directory: Path) -> int:
        """Load all workflow plans from a directory.

        Args:
            directory: Directory containing workflow plan JSON files

        Returns:
            Number of plans loaded

        Raises:
            PlanLoadError: If any plan fails to load
        """
        plans = self.loader.load_all(directory)
        for plan in plans:
            self.register(plan)
        return len(plans)

    def load_file(self, path: Path) -> WorkflowPlan:
        """Load a single workflow plan from file.

        Args:
            path: Path to the workflow plan JSON file

        Returns:
            The loaded WorkflowPlan

        Raises:
            PlanLoadError: If loading fails
        """
        plan = self.loader.load(path)
        self.register(plan)
        return plan


# Global registry instance for convenience
_global_registry: Optional[PlanRegistry] = None


def get_plan_registry() -> PlanRegistry:
    """Get the global plan registry instance.

    Creates a new instance if one doesn't exist.
    Auto-loads workflows from combine-config/workflows directory.
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = PlanRegistry()
        # Auto-load workflows from combine-config (versioned structure)
        workflow_dir = Path("combine-config/workflows")
        if workflow_dir.exists():
            try:
                count = _global_registry.load_from_directory(workflow_dir)
                import logging
                logging.getLogger(__name__).info(f"Loaded {count} workflow plans from {workflow_dir}")
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to auto-load workflows: {e}")
    return _global_registry


def reset_plan_registry() -> None:
    """Reset the global plan registry (useful for testing)."""
    global _global_registry
    _global_registry = None
