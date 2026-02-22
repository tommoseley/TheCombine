"""Loader for Document Interaction Workflow Plans (ADR-039).

Loads, validates, and parses workflow plan JSON files into typed models.
Supports combine-config/ versioned structure with active_releases.json.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.domain.workflow.plan_models import WorkflowPlan
from app.domain.workflow.plan_validator import (
    PlanValidationError,
    PlanValidator,
)

logger = logging.getLogger(__name__)


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
        plan = loader.load(Path("combine-config/workflows/concierge_intake/releases/1.0.0/definition.json"))
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

        Supports two structures:
        1. Flat: directory/*.json (legacy flat structure)
        2. Versioned: directory/{workflow_id}/releases/{version}/definition.json
           Uses _active/active_releases.json for version resolution.

        Args:
            directory: Directory containing workflow plans

        Returns:
            List of loaded WorkflowPlans

        Raises:
            PlanLoadError: If any plan fails to load
        """
        plans = []

        # Check for versioned structure (combine-config style)
        active_releases = self._load_active_releases(directory)
        if active_releases:
            # Load from versioned structure
            for workflow_id, version in active_releases.get("workflows", {}).items():
                definition_path = directory / workflow_id / "releases" / version / "definition.json"
                if definition_path.exists():
                    try:
                        plan = self.load(definition_path)
                        plans.append(plan)
                        logger.debug(f"Loaded workflow {workflow_id} v{version}")
                    except PlanLoadError as e:
                        logger.warning(f"Failed to load workflow {workflow_id}: {e}")
                else:
                    logger.warning(f"Workflow definition not found: {definition_path}")
        else:
            # Fall back to flat structure (legacy)
            for path in sorted(directory.glob("*.json")):
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

    def _load_active_releases(self, directory: Path) -> Optional[Dict[str, Any]]:
        """Load active_releases.json from combine-config structure.

        Args:
            directory: The workflows directory (e.g., combine-config/workflows/)

        Returns:
            Parsed active_releases dict or None if not found
        """
        # active_releases.json is at combine-config/_active/active_releases.json
        # If directory is combine-config/workflows, look in parent/_active/
        active_path = directory.parent / "_active" / "active_releases.json"
        if active_path.exists():
            try:
                with open(active_path, "r", encoding="utf-8-sig") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load active_releases.json: {e}")
        return None
