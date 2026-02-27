"""Prompt loader - load role and task prompts from combine-config/prompts/.

Provides access to governed prompt artifacts using PackageLoader.
Maintains backward compatibility with legacy name formats.
"""

import re
from pathlib import Path
from typing import Optional
import logging

from app.config.package_loader import (
    PackageNotFoundError,
    VersionNotFoundError,
    get_package_loader,
)


logger = logging.getLogger(__name__)


class PromptNotFoundError(Exception):
    """Raised when a prompt file is not found."""
    pass


def _parse_ref_format(ref: str) -> tuple[str, Optional[str]] | None:
    """
    Parse a colon-based reference format into (id, version).

    Examples:
        "prompt:task:intake_gate:1.0.0" -> ("intake_gate", "1.0.0")
        "prompt:role:technical_architect:1.0.0" -> ("technical_architect", "1.0.0")
        "mech:extractor:foo:1.0.0" -> None (not a prompt ref)

    Returns:
        (id, version) tuple if valid prompt ref, None otherwise
    """
    # Check for prompt:task: or prompt:role: prefix
    if ref.startswith("prompt:task:"):
        rest = ref[12:]  # Remove "prompt:task:"
    elif ref.startswith("prompt:role:"):
        rest = ref[12:]  # Remove "prompt:role:"
    else:
        return None

    # Split remaining by colon to get id and version
    parts = rest.rsplit(":", 1)
    if len(parts) == 2:
        task_id, version = parts
        # Validate version format (x.y.z)
        if re.match(r'^\d+\.\d+\.\d+$', version):
            return task_id, version
    # No version specified
    return parts[0], None


def _parse_legacy_name(name: str) -> tuple[str, Optional[str]]:
    """
    Parse a legacy prompt name into (id, version).

    Examples:
        "Technical Architect 1.0" -> ("technical_architect", "1.0.0")
        "Project Discovery v1.4" -> ("project_discovery", "1.4.0")
        "technical_architect" -> ("technical_architect", None)
    """
    # Already in new format (snake_case without version)
    if re.match(r'^[a-z][a-z0-9_]*$', name):
        return name, None

    # Extract version from end (e.g., "1.0", "v1.4")
    version_match = re.search(r'\s*v?(\d+\.\d+)$', name, re.IGNORECASE)
    if version_match:
        version = version_match.group(1) + ".0"  # Convert 1.0 to 1.0.0
        name = name[:version_match.start()]
    else:
        version = None

    # Convert to snake_case
    name_id = name.lower().strip().replace(' ', '_').replace('-', '_')
    name_id = re.sub(r'_+', '_', name_id).strip('_')

    return name_id, version


class PromptLoader:
    """Load role and task prompts from combine-config/prompts/.

    Uses PackageLoader internally but maintains backward compatibility
    with legacy prompt name formats.

    Legacy format mapping:
    - "Technical Architect 1.0" -> get_role("technical_architect", "1.0.0")
    - "Project Discovery v1.4" -> get_task("project_discovery", "1.4.0")

    Usage:
        loader = PromptLoader()
        role_prompt = loader.load_role("Technical Architect 1.0")
        task_prompt = loader.load_task("Project Discovery v1.4")

        # Or with new format:
        role_prompt = loader.load_role("technical_architect")  # Uses active release
    """

    def __init__(self, prompts_dir: Optional[Path] = None):
        """Initialize loader.

        Args:
            prompts_dir: Ignored (for backward compatibility).
                        Uses PackageLoader's combine-config path.
        """
        self._loader = get_package_loader()

        # Cache loaded prompts
        self._role_cache: dict[str, str] = {}
        self._task_cache: dict[str, str] = {}

    def load_role(self, role_name: str) -> str:
        """Load a role prompt by name.

        Args:
            role_name: Role name. Supports formats:
                - Ref: "prompt:role:technical_architect:1.0.0"
                - Legacy: "Technical Architect 1.0"
                - New: "technical_architect" (uses active release)
                - ADR-041: "roles/Technical Architect 1.0"

        Returns:
            Role prompt content

        Raises:
            PromptNotFoundError: If role prompt not found
        """
        if role_name in self._role_cache:
            return self._role_cache[role_name]

        # Check for colon-based ref format first (prompt:role:id:version)
        ref_result = _parse_ref_format(role_name)
        if ref_result is not None:
            role_id, version = ref_result
            try:
                role = self._loader.get_role(role_id, version)
                content = role.content
                self._role_cache[role_name] = content
                logger.info(f"PromptLoader: Loaded role prompt (ref): {role_id} v{role.version} ({len(content)} chars)")
                return content
            except (PackageNotFoundError, VersionNotFoundError) as e:
                available = self.list_roles()
                raise PromptNotFoundError(
                    f"Role prompt '{role_name}' not found (resolved to: {role_id}). "
                    f"Available: {', '.join(available) if available else '(none)'}"
                ) from e

        # Strip "roles/" prefix if present (ADR-041 format)
        if role_name.startswith("roles/"):
            role_name = role_name[6:]

        # Parse legacy name
        role_id, version = _parse_legacy_name(role_name)

        try:
            role = self._loader.get_role(role_id, version)
            content = role.content
            self._role_cache[role_name] = content
            logger.info(f"PromptLoader: Loaded role prompt: {role_id} v{role.version} ({len(content)} chars)")
            return content
        except (PackageNotFoundError, VersionNotFoundError) as e:
            available = self.list_roles()
            raise PromptNotFoundError(
                f"Role prompt '{role_name}' not found (resolved to: {role_id}). "
                f"Available: {', '.join(available) if available else '(none)'}"
            ) from e

    def load_task(self, task_name: str) -> str:
        """Load a task prompt by name.

        Args:
            task_name: Task name. Supports formats:
                - Ref: "prompt:task:intake_gate:1.0.0"
                - Legacy: "Project Discovery v1.4"
                - New: "project_discovery" (uses active release)
                - ADR-041: "tasks/Project Discovery v1.0"

        Returns:
            Task prompt content

        Raises:
            PromptNotFoundError: If task prompt not found
        """
        if task_name in self._task_cache:
            return self._task_cache[task_name]

        # Check for colon-based ref format first (prompt:task:id:version)
        ref_result = _parse_ref_format(task_name)
        if ref_result is not None:
            task_id, version = ref_result
            try:
                task = self._loader.get_task(task_id, version)
                content = task.content
                self._task_cache[task_name] = content
                logger.info(f"PromptLoader: Loaded task prompt (ref): {task_id} v{task.version} ({len(content)} chars)")
                return content
            except (PackageNotFoundError, VersionNotFoundError) as e:
                available = self.list_tasks()
                raise PromptNotFoundError(
                    f"Task prompt '{task_name}' not found (resolved to: {task_id}). "
                    f"Available: {', '.join(available) if available else '(none)'}"
                ) from e

        # Strip "tasks/" or "templates/" prefix if present (ADR-041 format)
        if task_name.startswith("tasks/"):
            task_name = task_name[6:]
        elif task_name.startswith("templates/"):
            # Templates are now separate - try to load from templates
            template_name = task_name[10:]
            template_id, version = _parse_legacy_name(template_name)
            try:
                template = self._loader.get_template(template_id, version)
                content = template.content
                self._task_cache[task_name] = content
                logger.info(f"PromptLoader: Loaded template: {template_id} v{template.version} ({len(content)} chars)")
                return content
            except (PackageNotFoundError, VersionNotFoundError) as e:
                raise PromptNotFoundError(
                    f"Template '{template_name}' not found (resolved to: {template_id})."
                ) from e

        # Parse legacy name
        task_id, version = _parse_legacy_name(task_name)

        try:
            task = self._loader.get_task(task_id, version)
            content = task.content
            self._task_cache[task_name] = content
            logger.info(f"PromptLoader: Loaded task prompt: {task_id} v{task.version} ({len(content)} chars)")
            return content
        except (PackageNotFoundError, VersionNotFoundError) as e:
            available = self.list_tasks()
            raise PromptNotFoundError(
                f"Task prompt '{task_name}' not found (resolved to: {task_id}). "
                f"Available: {', '.join(available) if available else '(none)'}"
            ) from e

    def list_roles(self) -> list[str]:
        """List available role prompt IDs."""
        return self._loader.list_roles()

    def list_tasks(self) -> list[str]:
        """List available task prompt IDs."""
        return self._loader.list_tasks()

    def clear_cache(self) -> None:
        """Clear the prompt cache."""
        self._role_cache.clear()
        self._task_cache.clear()

    def role_exists(self, role_name: str) -> bool:
        """Check if a role prompt exists."""
        if role_name.startswith("roles/"):
            role_name = role_name[6:]
        role_id, version = _parse_legacy_name(role_name)
        try:
            self._loader.get_role(role_id, version)
            return True
        except (PackageNotFoundError, VersionNotFoundError):
            return False

    def task_exists(self, task_name: str) -> bool:
        """Check if a task prompt exists."""
        if task_name.startswith("tasks/"):
            task_name = task_name[6:]
        task_id, version = _parse_legacy_name(task_name)
        try:
            self._loader.get_task(task_id, version)
            return True
        except (PackageNotFoundError, VersionNotFoundError):
            return False
