"""Loader for Document Interaction Workflow Plans (ADR-039).

Loads, validates, and parses workflow plan JSON files into typed models.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.domain.workflow.plan_models import WorkflowPlan
from app.domain.workflow.plan_validator import (
    PlanValidationError,
    PlanValidator,
)


class PlanLoadError(Exception):
    """Raised when plan loading fails."""

    def __init__(
        self,
        message: str,
        errors: Optional[List[PlanValidationError]] = None,
    ):
        super().__init__(message)
        self.errors = errors or []

    def __str__(self) -> str:
        if self.errors:
            error_msgs = [f"  - {e.message}" for e in self.errors[:5]]
            if len(self.errors) > 5:
                error_msgs.append(f"  ... and {len(self.errors) - 5} more errors")
            return f"{self.args[0]}\n" + "\n".join(error_msgs)
        return self.args[0]


class PlanLoader:
    """Load and parse workflow plan definitions.

    Usage:
        loader = PlanLoader()
        plan = loader.load(Path("seed/workflows/concierge_intake.v1.json"))
    """

    def __init__(self, validator: Optional[PlanValidator] = None):
        """Initialize loader with optional custom validator."""
        self.validator = validator or PlanValidator()

    def load(self, path: Path) -> WorkflowPlan:
        """Load workflow plan from file path.

        Args:
            path: Path to workflow plan JSON file

        Returns:
            Parsed and validated WorkflowPlan

        Raises:
            PlanLoadError: If file not found or validation fails
        """
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                raw = json.load(f)
        except FileNotFoundError:
            raise PlanLoadError(f"Workflow plan file not found: {path}")
        except json.JSONDecodeError as e:
            raise PlanLoadError(f"Invalid JSON in {path}: {e}")

        return self.load_dict(raw, source_path=str(path))

    def load_dict(
        self,
        raw: Dict[str, Any],
        source_path: Optional[str] = None,
    ) -> WorkflowPlan:
        """Load workflow plan from dictionary.

        Args:
            raw: Raw plan dict (e.g., from JSON)
            source_path: Optional source path for error messages

        Returns:
            Parsed and validated WorkflowPlan

        Raises:
            PlanLoadError: If validation fails
        """
        # Validate first
        result = self.validator.validate(raw)
        if not result.valid:
            source = f" in {source_path}" if source_path else ""
            raise PlanLoadError(
                f"Workflow plan validation failed{source} with {len(result.errors)} error(s)",
                errors=result.errors,
            )

        # Parse into typed model
        return WorkflowPlan.from_dict(raw)

    def load_all(self, directory: Path) -> List[WorkflowPlan]:
        """Load all workflow plans from a directory.

        Args:
            directory: Directory containing workflow plan JSON files

        Returns:
            List of loaded WorkflowPlans

        Raises:
            PlanLoadError: If any plan fails to load
        """
        plans = []
        for path in sorted(directory.glob("*.json")):
            # Skip non-plan files (e.g., schema files, old workflow.v1 files)
            try:
                with open(path, "r", encoding="utf-8-sig") as f:
                    raw = json.load(f)

                # Check if this looks like a workflow plan (has nodes/edges)
                if "nodes" in raw and "edges" in raw:
                    plan = self.load(path)
                    plans.append(plan)
            except (json.JSONDecodeError, PlanLoadError):
                # Skip files that aren't valid plans
                continue

        return plans
