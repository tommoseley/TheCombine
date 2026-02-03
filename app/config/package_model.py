"""
Document Type Package models.

Per ADR-044, these models represent the Git-canonical configuration
artifacts loaded from combine-config/.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import yaml


class AuthorityLevel(str, Enum):
    """Document authority level per ADR-044."""
    DESCRIPTIVE = "descriptive"
    PRESCRIPTIVE = "prescriptive"
    CONSTRUCTIVE = "constructive"
    ELABORATIVE = "elaborative"


class CreationMode(str, Enum):
    """How the document is created."""
    LLM_GENERATED = "llm_generated"
    CONSTRUCTED = "constructed"
    EXTRACTED = "extracted"


class ProductionMode(str, Enum):
    """Production semantics for workflow steps."""
    GENERATE = "generate"
    AUTHORIZE = "authorize"
    CONSTRUCT = "construct"


class Scope(str, Enum):
    """Document scope level."""
    PROJECT = "project"
    EPIC = "epic"
    FEATURE = "feature"


@dataclass
class PackageArtifacts:
    """Paths to packaged artifacts within a release directory."""
    task_prompt: Optional[str] = None
    qa_prompt: Optional[str] = None
    pgc_context: Optional[str] = None
    questions_prompt: Optional[str] = None
    schema: Optional[str] = None
    full_docdef: Optional[str] = None
    sidecar_docdef: Optional[str] = None
    gating_rules: Optional[str] = None
    workflow_fragment: Optional[str] = None


@dataclass
class PackageUI:
    """UI display configuration."""
    icon: Optional[str] = None
    category: Optional[str] = None
    display_order: Optional[int] = None


@dataclass
class PackageTests:
    """Test artifact paths."""
    fixtures: List[str] = field(default_factory=list)
    golden_traces: List[str] = field(default_factory=list)


@dataclass
class GatingRules:
    """Lifecycle and gating configuration."""
    lifecycle_states: List[str] = field(default_factory=list)
    design_status: List[str] = field(default_factory=list)
    acceptance_required: bool = False
    accepted_by: List[str] = field(default_factory=list)


@dataclass
class DocumentTypePackage:
    """
    A Document Type Package loaded from combine-config/.

    This is the atomic unit of configuration per ADR-044.
    """
    # Identity
    doc_type_id: str
    display_name: str
    version: str
    description: str = ""

    # Classification
    authority_level: AuthorityLevel = AuthorityLevel.ELABORATIVE
    creation_mode: CreationMode = CreationMode.LLM_GENERATED
    production_mode: Optional[ProductionMode] = None
    scope: Scope = Scope.PROJECT

    # Dependencies
    required_inputs: List[str] = field(default_factory=list)
    optional_inputs: List[str] = field(default_factory=list)
    creates_children: List[str] = field(default_factory=list)
    parent_doc_type: Optional[str] = None

    # Shared artifact references
    role_prompt_ref: Optional[str] = None
    template_ref: Optional[str] = None

    # Packaged artifacts
    artifacts: PackageArtifacts = field(default_factory=PackageArtifacts)

    # Tests
    tests: PackageTests = field(default_factory=PackageTests)

    # Gating
    gating_rules: GatingRules = field(default_factory=GatingRules)

    # UI
    ui: PackageUI = field(default_factory=PackageUI)

    # Internal: path to the release directory
    _release_path: Optional[Path] = field(default=None, repr=False)

    # Loaded content cache
    _task_prompt_content: Optional[str] = field(default=None, repr=False)
    _qa_prompt_content: Optional[str] = field(default=None, repr=False)
    _pgc_context_content: Optional[str] = field(default=None, repr=False)
    _questions_prompt_content: Optional[str] = field(default=None, repr=False)
    _schema_content: Optional[Dict[str, Any]] = field(default=None, repr=False)

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "DocumentTypePackage":
        """Load a package from a package.yaml file."""
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        release_path = yaml_path.parent

        # Parse artifacts
        artifacts_data = data.get("artifacts", {})
        artifacts = PackageArtifacts(
            task_prompt=artifacts_data.get("task_prompt"),
            qa_prompt=artifacts_data.get("qa_prompt"),
            pgc_context=artifacts_data.get("pgc_context"),
            questions_prompt=artifacts_data.get("questions_prompt"),
            schema=artifacts_data.get("schema"),
            full_docdef=artifacts_data.get("full_docdef"),
            sidecar_docdef=artifacts_data.get("sidecar_docdef"),
            gating_rules=artifacts_data.get("gating_rules"),
            workflow_fragment=artifacts_data.get("workflow_fragment"),
        )

        # Parse tests
        tests_data = data.get("tests", {})
        tests = PackageTests(
            fixtures=tests_data.get("fixtures", []),
            golden_traces=tests_data.get("golden_traces", []),
        )

        # Parse gating rules
        gating_data = data.get("gating_rules", {})
        gating_rules = GatingRules(
            lifecycle_states=gating_data.get("lifecycle_states", []),
            design_status=gating_data.get("design_status", []),
            acceptance_required=gating_data.get("acceptance_required", False),
            accepted_by=gating_data.get("accepted_by", []),
        )

        # Parse UI
        ui_data = data.get("ui", {})
        ui = PackageUI(
            icon=ui_data.get("icon"),
            category=ui_data.get("category"),
            display_order=ui_data.get("display_order"),
        )

        return cls(
            doc_type_id=data["doc_type_id"],
            display_name=data["display_name"],
            version=data["version"],
            description=data.get("description", ""),
            authority_level=AuthorityLevel(data.get("authority_level", "elaborative")),
            creation_mode=CreationMode(data.get("creation_mode", "llm_generated")),
            production_mode=ProductionMode(data["production_mode"]) if data.get("production_mode") else None,
            scope=Scope(data.get("scope", "project")),
            required_inputs=data.get("required_inputs", []),
            optional_inputs=data.get("optional_inputs", []),
            creates_children=data.get("creates_children", []),
            parent_doc_type=data.get("parent_doc_type"),
            role_prompt_ref=data.get("role_prompt_ref"),
            template_ref=data.get("template_ref"),
            artifacts=artifacts,
            tests=tests,
            gating_rules=gating_rules,
            ui=ui,
            _release_path=release_path,
        )

    def get_task_prompt(self) -> Optional[str]:
        """Load and return the task prompt content."""
        if self._task_prompt_content is not None:
            return self._task_prompt_content

        if not self.artifacts.task_prompt or not self._release_path:
            return None

        path = self._release_path / self.artifacts.task_prompt
        if path.exists():
            self._task_prompt_content = path.read_text(encoding="utf-8")
            return self._task_prompt_content
        return None

    def get_qa_prompt(self) -> Optional[str]:
        """Load and return the QA prompt content."""
        if self._qa_prompt_content is not None:
            return self._qa_prompt_content

        if not self.artifacts.qa_prompt or not self._release_path:
            return None

        path = self._release_path / self.artifacts.qa_prompt
        if path.exists():
            self._qa_prompt_content = path.read_text(encoding="utf-8")
            return self._qa_prompt_content
        return None

    def get_pgc_context(self) -> Optional[str]:
        """Load and return the PGC context content."""
        if self._pgc_context_content is not None:
            return self._pgc_context_content

        if not self.artifacts.pgc_context or not self._release_path:
            return None

        path = self._release_path / self.artifacts.pgc_context
        if path.exists():
            self._pgc_context_content = path.read_text(encoding="utf-8")
            return self._pgc_context_content
        return None

    def get_schema(self) -> Optional[Dict[str, Any]]:
        """Load and return the output schema."""
        if self._schema_content is not None:
            return self._schema_content

        if not self.artifacts.schema or not self._release_path:
            return None

        path = self._release_path / self.artifacts.schema
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                self._schema_content = json.load(f)
            return self._schema_content
        return None

    def requires_pgc(self) -> bool:
        """Check if this document type requires PGC context."""
        return self.authority_level in (
            AuthorityLevel.DESCRIPTIVE,
            AuthorityLevel.PRESCRIPTIVE,
        )

    def is_llm_generated(self) -> bool:
        """Check if this document is LLM-generated."""
        return self.creation_mode == CreationMode.LLM_GENERATED


@dataclass
class RolePrompt:
    """A shared role prompt loaded from combine-config/prompts/roles/."""
    role_id: str
    version: str
    content: str
    _release_path: Optional[Path] = field(default=None, repr=False)

    @classmethod
    def from_path(cls, release_path: Path, role_id: str, version: str) -> "RolePrompt":
        """Load a role prompt from a release directory."""
        prompt_path = release_path / "role.prompt.txt"
        content = prompt_path.read_text(encoding="utf-8")
        return cls(
            role_id=role_id,
            version=version,
            content=content,
            _release_path=release_path,
        )


@dataclass
class Template:
    """A shared template loaded from combine-config/prompts/templates/."""
    template_id: str
    version: str
    content: str
    _release_path: Optional[Path] = field(default=None, repr=False)

    @classmethod
    def from_path(cls, release_path: Path, template_id: str, version: str) -> "Template":
        """Load a template from a release directory."""
        template_path = release_path / "template.txt"
        content = template_path.read_text(encoding="utf-8")
        return cls(
            template_id=template_id,
            version=version,
            content=content,
            _release_path=release_path,
        )


@dataclass
class ActiveReleases:
    """Active release pointers loaded from _active/active_releases.json."""
    document_types: Dict[str, str] = field(default_factory=dict)
    roles: Dict[str, str] = field(default_factory=dict)
    templates: Dict[str, str] = field(default_factory=dict)
    workflows: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_json(cls, json_path: Path) -> "ActiveReleases":
        """Load active releases from JSON file."""
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return cls(
            document_types=data.get("document_types", {}),
            roles=data.get("roles", {}),
            templates=data.get("templates", {}),
            workflows=data.get("workflows", {}),
        )

    def get_doc_type_version(self, doc_type_id: str) -> Optional[str]:
        """Get the active version for a document type."""
        return self.document_types.get(doc_type_id)

    def get_role_version(self, role_id: str) -> Optional[str]:
        """Get the active version for a role."""
        return self.roles.get(role_id)

    def get_template_version(self, template_id: str) -> Optional[str]:
        """Get the active version for a template."""
        return self.templates.get(template_id)
