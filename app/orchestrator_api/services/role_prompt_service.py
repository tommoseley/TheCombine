"""Role prompt service for building prompts from database."""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from app.orchestrator_api.persistence.repositories.role_prompt_repository import (
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
        pipeline_id: str,
        phase: str,
        epic_context: Optional[str] = None,
        pipeline_state: Optional[Dict[str, Any]] = None,
        artifacts: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str]:
        """
        Build complete role prompt with all sections.

        NOTE: Does NOT record usage - that happens in 175B when PhaseExecutorService
        actually uses the prompt. 175A is infrastructure-only.

        Args:
            role_name: Role identifier (pm, architect, ba, dev, qa, commit)
            pipeline_id: Pipeline identifier
            phase: Current phase
            epic_context: Epic description (optional)
            pipeline_state: Pipeline state as dict (optional)
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
        # Make created_at timezone-aware if it's naive (SQLite stores naive datetimes)
        created_at = prompt.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        
        age_days = (datetime.now(timezone.utc) - created_at).days
        if age_days > 365:
            logger.warning(
                f"Role prompt for '{role_name}' is {age_days} days old. "
                f"Consider creating new version."
            )

        # Build sections
        sections = []

        # Starting prompt (optional)
        if prompt.starting_prompt:
            sections.append(prompt.starting_prompt)
            sections.append("")  # Blank line

        # Role Bootstrap (required)
        sections.append("# Role Bootstrap")
        sections.append("")
        sections.append(prompt.bootstrapper)
        sections.append("")

        # Instructions (required)
        sections.append("# Instructions")
        sections.append("")
        sections.append(prompt.instructions)
        sections.append("")

        # Working Schema (optional)
        if prompt.working_schema:
            sections.append("# Working Schema")
            sections.append("")
            sections.append("```json")
            sections.append(json.dumps(prompt.working_schema, indent=2))
            sections.append("```")
            sections.append("")

        # # Epic Context (optional)
        # if epic_context:
        #     sections.append("# Epic Context")
        #     sections.append("")
        #     sections.append(epic_context)
        #     sections.append("")

        # Pipeline State (optional)
        if pipeline_state:
            sections.append("# Pipeline State")
            sections.append("")
            sections.append("```json")
            sections.append(json.dumps(pipeline_state, indent=2))
            sections.append("```")
            sections.append("")

        # Previous Artifacts (optional, skip if empty dict)
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