"""
Package Loader for Git-canonical configuration.

Per ADR-044, this module loads Document Type Packages and shared artifacts
from the combine-config/ repository.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from app.config.package_model import (
    DocumentTypePackage,
    RolePrompt,
    StandaloneSchema,
    TaskPrompt,
    PgcContext,
    Template,
    ActiveReleases,
)

logger = logging.getLogger(__name__)

# Default path to combine-config (relative to project root)
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "combine-config"


class PackageLoaderError(Exception):
    """Error loading a package or artifact."""
    pass


class PackageNotFoundError(PackageLoaderError):
    """Package or artifact not found."""
    pass


class VersionNotFoundError(PackageLoaderError):
    """Requested version not found."""
    pass


class PackageLoader:
    """
    Loads Document Type Packages and shared artifacts from combine-config/.

    This is the primary interface for accessing Git-canonical configuration
    at runtime. All configuration access should go through this class.

    Usage:
        loader = PackageLoader()
        package = loader.get_document_type("project_discovery")
        role = loader.get_role("technical_architect")
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the package loader.

        Args:
            config_path: Path to combine-config/ directory.
                        Defaults to combine-config/ in project root.
        """
        self.config_path = config_path or DEFAULT_CONFIG_PATH

        if not self.config_path.exists():
            raise PackageLoaderError(f"Config path does not exist: {self.config_path}")

        # Paths
        self._active_releases_path = self.config_path / "_active" / "active_releases.json"
        self._document_types_path = self.config_path / "document_types"
        self._roles_path = self.config_path / "prompts" / "roles"
        self._templates_path = self.config_path / "prompts" / "templates"
        self._tasks_path = self.config_path / "prompts" / "tasks"
        self._pgc_path = self.config_path / "prompts" / "pgc"
        self._schemas_path = self.config_path / "schemas"

        # Caches
        self._active_releases: Optional[ActiveReleases] = None
        self._package_cache: Dict[str, DocumentTypePackage] = {}
        self._role_cache: Dict[str, RolePrompt] = {}
        self._template_cache: Dict[str, Template] = {}
        self._task_cache: Dict[str, TaskPrompt] = {}
        self._pgc_cache: Dict[str, PgcContext] = {}
        self._schema_cache: Dict[str, StandaloneSchema] = {}

    def get_active_releases(self) -> ActiveReleases:
        """Load and return the active releases configuration."""
        if self._active_releases is None:
            if not self._active_releases_path.exists():
                raise PackageLoaderError(
                    f"Active releases file not found: {self._active_releases_path}"
                )
            self._active_releases = ActiveReleases.from_json(self._active_releases_path)
            logger.debug(f"Loaded active releases: {self._active_releases.document_types}")

        return self._active_releases

    def invalidate_cache(self) -> None:
        """Invalidate all caches. Call after config changes."""
        self._active_releases = None
        self._package_cache.clear()
        self._role_cache.clear()
        self._template_cache.clear()
        self._task_cache.clear()
        self._pgc_cache.clear()
        self._schema_cache.clear()
        logger.info("Package loader cache invalidated")

    # =========================================================================
    # Document Type Packages
    # =========================================================================

    def get_document_type(
        self,
        doc_type_id: str,
        version: Optional[str] = None,
    ) -> DocumentTypePackage:
        """
        Load a Document Type Package.

        Args:
            doc_type_id: Document type identifier (e.g., "project_discovery")
            version: Specific version to load. If None, uses active release.

        Returns:
            Loaded DocumentTypePackage

        Raises:
            PackageNotFoundError: Document type not found
            VersionNotFoundError: Requested version not found
        """
        # Determine version
        if version is None:
            active = self.get_active_releases()
            version = active.get_doc_type_version(doc_type_id)
            if version is None:
                raise PackageNotFoundError(
                    f"No active release for document type: {doc_type_id}"
                )

        # Check cache
        cache_key = f"{doc_type_id}:{version}"
        if cache_key in self._package_cache:
            return self._package_cache[cache_key]

        # Load package
        package_path = self._document_types_path / doc_type_id / "releases" / version
        if not package_path.exists():
            raise VersionNotFoundError(
                f"Version {version} not found for document type: {doc_type_id}"
            )

        manifest_path = package_path / "package.yaml"
        if not manifest_path.exists():
            raise PackageLoaderError(
                f"Package manifest not found: {manifest_path}"
            )

        package = DocumentTypePackage.from_yaml(manifest_path)
        self._package_cache[cache_key] = package

        logger.debug(f"Loaded document type package: {doc_type_id} v{version}")
        return package

    def list_document_types(self) -> List[str]:
        """List all available document type IDs."""
        if not self._document_types_path.exists():
            return []

        return [
            d.name for d in self._document_types_path.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

    def list_document_type_versions(self, doc_type_id: str) -> List[str]:
        """List all available versions for a document type."""
        releases_path = self._document_types_path / doc_type_id / "releases"
        if not releases_path.exists():
            return []

        return sorted([
            d.name for d in releases_path.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ])

    # =========================================================================
    # Role Prompts
    # =========================================================================

    def get_role(
        self,
        role_id: str,
        version: Optional[str] = None,
    ) -> RolePrompt:
        """
        Load a shared role prompt.

        Args:
            role_id: Role identifier (e.g., "technical_architect")
            version: Specific version to load. If None, uses active release.

        Returns:
            Loaded RolePrompt

        Raises:
            PackageNotFoundError: Role not found
            VersionNotFoundError: Requested version not found
        """
        # Determine version
        if version is None:
            active = self.get_active_releases()
            version = active.get_role_version(role_id)
            if version is None:
                raise PackageNotFoundError(
                    f"No active release for role: {role_id}"
                )

        # Check cache
        cache_key = f"{role_id}:{version}"
        if cache_key in self._role_cache:
            return self._role_cache[cache_key]

        # Load role
        role_path = self._roles_path / role_id / "releases" / version
        if not role_path.exists():
            raise VersionNotFoundError(
                f"Version {version} not found for role: {role_id}"
            )

        role = RolePrompt.from_path(role_path, role_id, version)
        self._role_cache[cache_key] = role

        logger.debug(f"Loaded role prompt: {role_id} v{version}")
        return role

    def list_roles(self) -> List[str]:
        """List all available role IDs."""
        if not self._roles_path.exists():
            return []

        return [
            d.name for d in self._roles_path.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

    # =========================================================================
    # Templates
    # =========================================================================

    def get_template(
        self,
        template_id: str,
        version: Optional[str] = None,
    ) -> Template:
        """
        Load a shared template.

        Args:
            template_id: Template identifier (e.g., "document_generator")
            version: Specific version to load. If None, uses active release.

        Returns:
            Loaded Template

        Raises:
            PackageNotFoundError: Template not found
            VersionNotFoundError: Requested version not found
        """
        # Determine version
        if version is None:
            active = self.get_active_releases()
            version = active.get_template_version(template_id)
            if version is None:
                raise PackageNotFoundError(
                    f"No active release for template: {template_id}"
                )

        # Check cache
        cache_key = f"{template_id}:{version}"
        if cache_key in self._template_cache:
            return self._template_cache[cache_key]

        # Load template
        template_path = self._templates_path / template_id / "releases" / version
        if not template_path.exists():
            raise VersionNotFoundError(
                f"Version {version} not found for template: {template_id}"
            )

        template = Template.from_path(template_path, template_id, version)
        self._template_cache[cache_key] = template

        logger.debug(f"Loaded template: {template_id} v{version}")
        return template

    def list_templates(self) -> List[str]:
        """List all available template IDs."""
        if not self._templates_path.exists():
            return []

        return [
            d.name for d in self._templates_path.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

    # =========================================================================
    # Task Prompts
    # =========================================================================

    def get_task(
        self,
        task_id: str,
        version: Optional[str] = None,
    ) -> TaskPrompt:
        """
        Load a standalone task prompt.

        Args:
            task_id: Task identifier (e.g., "project_discovery")
            version: Specific version to load. If None, uses active release.

        Returns:
            Loaded TaskPrompt

        Raises:
            PackageNotFoundError: Task not found
            VersionNotFoundError: Requested version not found
        """
        # Determine version
        if version is None:
            active = self.get_active_releases()
            version = active.get_task_version(task_id)
            if version is None:
                raise PackageNotFoundError(
                    f"No active release for task: {task_id}"
                )

        # Check cache
        cache_key = f"{task_id}:{version}"
        if cache_key in self._task_cache:
            return self._task_cache[cache_key]

        # Load task
        task_path = self._tasks_path / task_id / "releases" / version
        if not task_path.exists():
            raise VersionNotFoundError(
                f"Version {version} not found for task: {task_id}"
            )

        task = TaskPrompt.from_path(task_path, task_id, version)
        self._task_cache[cache_key] = task

        logger.debug(f"Loaded task prompt: {task_id} v{version}")
        return task

    def list_tasks(self) -> List[str]:
        """List all available task IDs."""
        if not self._tasks_path.exists():
            return []

        return [
            d.name for d in self._tasks_path.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

    # =========================================================================
    # PGC Contexts
    # =========================================================================

    def get_pgc(
        self,
        pgc_id: str,
        version: Optional[str] = None,
    ) -> PgcContext:
        """
        Load a PGC context.

        Args:
            pgc_id: PGC identifier (e.g., "project_discovery.v1")
            version: Specific version to load. If None, uses active release.

        Returns:
            Loaded PgcContext

        Raises:
            PackageNotFoundError: PGC context not found
            VersionNotFoundError: Requested version not found
        """
        # Determine version
        if version is None:
            active = self.get_active_releases()
            version = active.get_pgc_version(pgc_id)
            if version is None:
                raise PackageNotFoundError(
                    f"No active release for PGC: {pgc_id}"
                )

        # Check cache
        cache_key = f"{pgc_id}:{version}"
        if cache_key in self._pgc_cache:
            return self._pgc_cache[cache_key]

        # Load PGC
        pgc_path = self._pgc_path / pgc_id / "releases" / version
        if not pgc_path.exists():
            raise VersionNotFoundError(
                f"Version {version} not found for PGC: {pgc_id}"
            )

        pgc = PgcContext.from_path(pgc_path, pgc_id, version)
        self._pgc_cache[cache_key] = pgc

        logger.debug(f"Loaded PGC context: {pgc_id} v{version}")
        return pgc

    def list_pgc(self) -> List[str]:
        """List all available PGC context IDs."""
        if not self._pgc_path.exists():
            return []

        return [
            d.name for d in self._pgc_path.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

    # =========================================================================
    # Standalone Schemas
    # =========================================================================

    def get_schema(
        self,
        schema_id: str,
        version: Optional[str] = None,
    ) -> StandaloneSchema:
        """
        Load a standalone schema.

        Args:
            schema_id: Schema identifier (e.g., "project_discovery")
            version: Specific version to load. If None, uses active release.

        Returns:
            Loaded StandaloneSchema

        Raises:
            PackageNotFoundError: Schema not found
            VersionNotFoundError: Requested version not found
        """
        # Determine version
        if version is None:
            active = self.get_active_releases()
            version = active.get_schema_version(schema_id)
            if version is None:
                raise PackageNotFoundError(
                    f"No active release for schema: {schema_id}"
                )

        # Check cache
        cache_key = f"{schema_id}:{version}"
        if cache_key in self._schema_cache:
            return self._schema_cache[cache_key]

        # Load schema
        schema_path = self._schemas_path / schema_id / "releases" / version
        if not schema_path.exists():
            raise VersionNotFoundError(
                f"Version {version} not found for schema: {schema_id}"
            )

        schema = StandaloneSchema.from_path(schema_path, schema_id, version)
        self._schema_cache[cache_key] = schema

        logger.debug(f"Loaded standalone schema: {schema_id} v{version}")
        return schema

    def list_schemas(self) -> List[str]:
        """List all available standalone schema IDs."""
        if not self._schemas_path.exists():
            return []

        return [
            d.name for d in self._schemas_path.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    def resolve_role_for_package(
        self,
        package: DocumentTypePackage,
    ) -> Optional[RolePrompt]:
        """
        Resolve and load the role prompt referenced by a package.

        Args:
            package: The document type package

        Returns:
            Loaded RolePrompt or None if no role reference
        """
        if not package.role_prompt_ref:
            return None

        # Parse reference: prompt:role:{role_id}:{version}
        parts = package.role_prompt_ref.split(":")
        if len(parts) != 4 or parts[0] != "prompt" or parts[1] != "role":
            logger.warning(f"Invalid role prompt ref: {package.role_prompt_ref}")
            return None

        role_id = parts[2]
        version = parts[3]

        return self.get_role(role_id, version)

    def resolve_schema_for_package(
        self,
        package: DocumentTypePackage,
    ) -> Optional[Dict]:
        """
        Resolve and load the schema for a package.

        Dual-read: checks standalone schema (via schema_ref) first,
        falls back to packaged schema.

        Args:
            package: The document type package

        Returns:
            Schema dict or None if no schema available
        """
        # Try standalone schema first (via schema_ref)
        if package.schema_ref:
            parts = package.schema_ref.split(":")
            if len(parts) == 3 and parts[0] == "schema":
                schema_id = parts[1]
                version = parts[2]
                try:
                    standalone = self.get_schema(schema_id, version)
                    return standalone.content
                except (PackageNotFoundError, VersionNotFoundError) as e:
                    logger.debug(
                        f"Standalone schema not found for {package.schema_ref}, "
                        f"falling back to packaged: {e}"
                    )

        # Fall back to packaged schema
        return package.get_schema()

    def resolve_template_for_package(
        self,
        package: DocumentTypePackage,
    ) -> Optional[Template]:
        """
        Resolve and load the template referenced by a package.

        Args:
            package: The document type package

        Returns:
            Loaded Template or None if no template reference
        """
        if not package.template_ref:
            return None

        # Parse reference: prompt:template:{template_id}:{version}
        parts = package.template_ref.split(":")
        if len(parts) != 4 or parts[0] != "prompt" or parts[1] != "template":
            logger.warning(f"Invalid template ref: {package.template_ref}")
            return None

        template_id = parts[2]
        version = parts[3]

        return self.get_template(template_id, version)

    def _resolve_template_ref(
        self,
        template_ref: str,
    ) -> Optional[Template]:
        """
        Resolve a template reference string to a Template.

        Args:
            template_ref: Reference string in format prompt:template:{template_id}:{version}

        Returns:
            Loaded Template or None if invalid reference
        """
        if not template_ref:
            return None

        # Parse reference: prompt:template:{template_id}:{version}
        parts = template_ref.split(":")
        if len(parts) != 4 or parts[0] != "prompt" or parts[1] != "template":
            logger.warning(f"Invalid template ref: {template_ref}")
            return None

        template_id = parts[2]
        version = parts[3]

        try:
            return self.get_template(template_id, version)
        except (PackageNotFoundError, VersionNotFoundError) as e:
            logger.warning(f"Failed to resolve template ref {template_ref}: {e}")
            return None

    def assemble_prompt(
        self,
        package: DocumentTypePackage,
    ) -> Optional[str]:
        """
        Assemble a complete prompt for a document type.

        Combines role prompt, task prompt, and schema using the template.

        Args:
            package: The document type package

        Returns:
            Assembled prompt string or None if unable to assemble
        """
        if not package.is_llm_generated():
            return None

        # Get components
        role = self.resolve_role_for_package(package)
        template = self.resolve_template_for_package(package)
        task_prompt = package.get_task_prompt()
        schema = self.resolve_schema_for_package(package)

        if not all([role, template, task_prompt]):
            logger.warning(
                f"Cannot assemble prompt for {package.doc_type_id}: "
                f"missing components (role={bool(role)}, template={bool(template)}, "
                f"task={bool(task_prompt)})"
            )
            return None

        # Assemble using template
        import json
        schema_str = json.dumps(schema, indent=2) if schema else ""

        assembled = template.content
        assembled = assembled.replace("$$ROLE_PROMPT", role.content)
        assembled = assembled.replace("$$TASK_PROMPT", task_prompt)
        assembled = assembled.replace("$$OUTPUT_SCHEMA", schema_str)

        return assembled

    def assemble_qa_prompt(
        self,
        package: DocumentTypePackage,
    ) -> Optional[str]:
        """
        Assemble a complete QA prompt for a document type.

        Uses qa_template_ref if specified, otherwise falls back to legacy assembly.

        Args:
            package: The document type package

        Returns:
            Assembled QA prompt string or None if not available
        """
        qa_prompt = package.get_qa_prompt()
        if not qa_prompt:
            return None

        # Get the QA role (quality_assurance)
        qa_role = self.get_role("quality_assurance")

        # Get QA schema if available
        import json
        schema = self.resolve_schema_for_package(package)
        schema_str = json.dumps(schema, indent=2) if schema else ""

        # Try to use QA template if specified
        if package.qa_template_ref:
            template = self._resolve_template_ref(package.qa_template_ref)
            if template:
                assembled = template.content
                assembled = assembled.replace("$$ROLE_PROMPT", qa_role.content if qa_role else "")
                assembled = assembled.replace("$$QA_PROMPT", qa_prompt)
                assembled = assembled.replace("$$OUTPUT_SCHEMA", schema_str)
                return assembled

        # Legacy fallback: manual assembly
        lines = []

        if qa_role:
            lines.append("# QA Role")
            lines.append("")
            lines.append(qa_role.content)
            lines.append("")
            lines.append("---")
            lines.append("")

        lines.append("# QA Prompt")
        lines.append("")
        lines.append(qa_prompt)

        return "\n".join(lines)

    def assemble_pgc_prompt(
        self,
        package: DocumentTypePackage,
    ) -> Optional[str]:
        """
        Assemble PGC prompt for a document type.

        Uses pgc_template_ref if specified, otherwise falls back to legacy assembly.

        Args:
            package: The document type package

        Returns:
            PGC prompt string or None if not available
        """
        pgc_context = package.get_pgc_context()
        if not pgc_context:
            return None

        # Get PGC schema if available (clarification questions schema)
        import json
        schema = self.resolve_schema_for_package(package)
        schema_str = json.dumps(schema, indent=2) if schema else ""

        # Try to use PGC template if specified
        if package.pgc_template_ref:
            template = self._resolve_template_ref(package.pgc_template_ref)
            if template:
                assembled = template.content
                assembled = assembled.replace("$$PGC_CONTEXT", pgc_context)
                assembled = assembled.replace("$$OUTPUT_SCHEMA", schema_str)
                return assembled

        # Legacy fallback: manual assembly
        lines = [
            f"# PGC Context for {package.display_name}",
            f"# Version: {package.version}",
            "",
            pgc_context,
        ]

        return "\n".join(lines)

    def assemble_reflection_prompt(
        self,
        package: DocumentTypePackage,
    ) -> Optional[str]:
        """
        Assemble a reflection prompt for a document type.

        Returns the reflection prompt content with header information.

        Args:
            package: The document type package

        Returns:
            Reflection prompt string or None if not available
        """
        reflection_prompt = package.get_reflection_prompt()
        if not reflection_prompt:
            return None

        # Get the QA role (used for reflection as well)
        qa_role = self.get_role("quality_assurance")

        # Build assembled reflection prompt
        lines = []

        if qa_role:
            lines.append("# Reflection Role")
            lines.append("")
            lines.append(qa_role.content)
            lines.append("")
            lines.append("---")
            lines.append("")

        lines.append("# Reflection Prompt")
        lines.append("")
        lines.append(reflection_prompt)

        return "\n".join(lines)


# Module-level singleton
_loader: Optional[PackageLoader] = None


def get_package_loader(config_path: Optional[Path] = None) -> PackageLoader:
    """
    Get the singleton PackageLoader instance.

    Args:
        config_path: Optional config path. Only used on first call.

    Returns:
        PackageLoader instance
    """
    global _loader

    if _loader is None:
        _loader = PackageLoader(config_path)

    return _loader


def reset_package_loader() -> None:
    """Reset the singleton (for testing)."""
    global _loader
    _loader = None
