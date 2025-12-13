"""Role prompt service for building prompts from database."""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from app.combine.repositories.role_prompt_repository import (
    RolePromptRepository,
)

logger = logging.getLogger(__name__)


class RolePromptService:
    """Service for building role prompts with context injection."""

    def __init__(self):
        """Initialize the service."""
        self.prompt_repo = RolePromptRepository()

    def build_prompt(
        self,
        role_name: str,
        pipeline_id: str = None,
        phase: str = None,
        epic_context: Optional[str] = None,
        pipeline_state: Optional[Dict[str, Any]] = None,
        artifacts: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str]:
        """
        Build complete role prompt with all sections.

        Args:
            role_name: Role identifier (pm, architect, ba, developer, qa)
            pipeline_id: Optional pipeline/artifact identifier (for legacy compatibility)
            phase: Optional phase (for legacy compatibility)
            epic_context: Epic description (optional)
            pipeline_state: State data (optional)
            artifacts: Previous artifacts as dict (optional)

        Returns:
            Tuple of (prompt_text, prompt_id) for execution and audit

        Raises:
            ValueError: If no active prompt found for role
        """
        # Load active prompt
        prompt = self.prompt_repo.get_active_prompt(role_name)
        if not prompt:
            raise ValueError(f"No active prompt found for role: {role_name}")

        # Warn if prompt is stale (>1 year old)
        created_at = prompt.created_at
        if created_at.tzinfo is None:
            # PostgreSQL TIMESTAMPTZ is always timezone-aware, but handle legacy SQLite
            created_at = created_at.replace(tzinfo=timezone.utc)
        
        age_days = (datetime.now(timezone.utc) - created_at).days
        if age_days > 365:
            logger.warning(
                f"Role prompt for '{role_name}' is {age_days} days old. "
                f"Consider creating new version."
            )

        # Build sections
        sections = []

        # Instructions (required) - this is the main prompt
        sections.append(prompt.instructions)
        sections.append("")

        # Expected Schema (optional)
        if prompt.expected_schema:
            sections.append("# Expected Output Schema")
            sections.append("")
            sections.append("```json")
            sections.append(json.dumps(prompt.expected_schema, indent=2))
            sections.append("```")
            sections.append("")

        # Epic Context (optional)
        if epic_context:
            sections.append("# Epic Context")
            sections.append("")
            sections.append(epic_context)
            sections.append("")

        # Pipeline/Artifact State (optional)
        if pipeline_state:
            sections.append("# Context State")
            sections.append("")
            sections.append("```json")
            sections.append(json.dumps(pipeline_state, indent=2))
            sections.append("```")
            sections.append("")

        # Previous Artifacts (optional)
        if artifacts:
            sections.append("# Previous Artifacts")
            sections.append("")
            sections.append("```json")
            sections.append(json.dumps(artifacts, indent=2))
            sections.append("```")
            sections.append("")

        # Join all sections
        prompt_text = "\n".join(sections)

        return prompt_text, prompt.id