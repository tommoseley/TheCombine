"""
Tests for the Package Loader.

These tests verify that the package loader correctly reads from
combine-config/ and resolves artifacts.
"""

import pytest
from pathlib import Path

from app.config.package_model import (
    DocumentTypePackage,
    AuthorityLevel,
    CreationMode,
    ProductionMode,
    Scope,
)
from app.config.package_loader import (
    PackageLoader,
    PackageNotFoundError,
    VersionNotFoundError,
    reset_package_loader,
)


# Path to combine-config in project root
CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "combine-config"


@pytest.fixture
def loader():
    """Create a package loader for testing."""
    reset_package_loader()
    return PackageLoader(CONFIG_PATH)


class TestActiveReleases:
    """Tests for active release loading."""

    def test_load_active_releases(self, loader):
        """Active releases should load from JSON."""
        active = loader.get_active_releases()

        assert active is not None
        assert "project_discovery" in active.document_types
        assert active.document_types["project_discovery"] == "1.4.0"

    def test_get_doc_type_version(self, loader):
        """Should return active version for document type."""
        active = loader.get_active_releases()

        version = active.get_doc_type_version("project_discovery")
        assert version == "1.4.0"

    def test_get_missing_doc_type_version(self, loader):
        """Should return None for unknown document type."""
        active = loader.get_active_releases()

        version = active.get_doc_type_version("nonexistent")
        assert version is None


class TestDocumentTypePackage:
    """Tests for document type package loading."""

    def test_load_project_discovery(self, loader):
        """Project Discovery package should load correctly."""
        package = loader.get_document_type("project_discovery")

        assert package.doc_type_id == "project_discovery"
        assert package.display_name == "Project Discovery"
        assert package.version == "1.4.0"
        assert package.authority_level == AuthorityLevel.DESCRIPTIVE
        assert package.creation_mode == CreationMode.LLM_GENERATED
        assert package.production_mode == ProductionMode.GENERATE
        assert package.scope == Scope.PROJECT

    def test_load_primary_implementation_plan(self, loader):
        """Primary Implementation Plan package should load correctly."""
        package = loader.get_document_type("primary_implementation_plan")

        assert package.doc_type_id == "primary_implementation_plan"
        assert package.authority_level == AuthorityLevel.PRESCRIPTIVE
        assert package.required_inputs == ["project_discovery"]

    def test_load_specific_version(self, loader):
        """Should load a specific version when requested."""
        package = loader.get_document_type("project_discovery", version="1.4.0")

        assert package.version == "1.4.0"

    def test_load_nonexistent_doc_type(self, loader):
        """Should raise PackageNotFoundError for unknown doc type."""
        with pytest.raises(PackageNotFoundError):
            loader.get_document_type("nonexistent")

    def test_load_nonexistent_version(self, loader):
        """Should raise VersionNotFoundError for unknown version."""
        with pytest.raises(VersionNotFoundError):
            loader.get_document_type("project_discovery", version="99.0.0")

    def test_get_task_prompt(self, loader):
        """Should load task prompt content."""
        package = loader.get_document_type("project_discovery")
        task_prompt = package.get_task_prompt()

        assert task_prompt is not None
        assert "Project Discovery" in task_prompt
        assert len(task_prompt) > 100

    def test_get_pgc_context(self, loader):
        """Should load PGC context content."""
        package = loader.get_document_type("project_discovery")
        pgc_context = package.get_pgc_context()

        assert pgc_context is not None
        assert "Project Discovery" in pgc_context

    def test_get_schema(self, loader):
        """Should load output schema."""
        package = loader.get_document_type("project_discovery")
        schema = package.get_schema()

        assert schema is not None
        assert schema["title"] == "Project Discovery"
        assert "unknowns" in schema["properties"]

    def test_requires_pgc(self, loader):
        """Descriptive documents should require PGC."""
        package = loader.get_document_type("project_discovery")
        assert package.requires_pgc() is True

    def test_is_llm_generated(self, loader):
        """Should correctly identify LLM-generated documents."""
        package = loader.get_document_type("project_discovery")
        assert package.is_llm_generated() is True


class TestRolePrompts:
    """Tests for role prompt loading."""

    def test_load_technical_architect(self, loader):
        """Technical Architect role should load correctly."""
        role = loader.get_role("technical_architect")

        assert role.role_id == "technical_architect"
        assert role.version == "1.0.0"
        assert "Technical Architect" in role.content

    def test_load_project_manager(self, loader):
        """Project Manager role should load correctly."""
        role = loader.get_role("project_manager")

        assert role.role_id == "project_manager"
        assert "Project Manager" in role.content

    def test_list_roles(self, loader):
        """Should list available roles."""
        roles = loader.list_roles()

        assert "technical_architect" in roles
        assert "project_manager" in roles


class TestTemplates:
    """Tests for template loading."""

    def test_load_document_generator(self, loader):
        """Document Generator template should load correctly."""
        template = loader.get_template("document_generator")

        assert template.template_id == "document_generator"
        assert "$$ROLE_PROMPT" in template.content
        assert "$$TASK_PROMPT" in template.content
        assert "$$OUTPUT_SCHEMA" in template.content


class TestPromptAssembly:
    """Tests for prompt assembly."""

    def test_resolve_role_for_package(self, loader):
        """Should resolve role prompt from package reference."""
        package = loader.get_document_type("project_discovery")
        role = loader.resolve_role_for_package(package)

        assert role is not None
        assert role.role_id == "technical_architect"

    def test_resolve_template_for_package(self, loader):
        """Should resolve template from package reference."""
        package = loader.get_document_type("project_discovery")
        template = loader.resolve_template_for_package(package)

        assert template is not None
        assert template.template_id == "document_generator"

    def test_assemble_prompt(self, loader):
        """Should assemble a complete prompt."""
        package = loader.get_document_type("project_discovery")
        prompt = loader.assemble_prompt(package)

        assert prompt is not None
        # Role content should be present
        assert "Technical Architect" in prompt
        # Task content should be present
        assert "Project Discovery" in prompt
        # Schema should be present
        assert '"unknowns"' in prompt


class TestCaching:
    """Tests for caching behavior."""

    def test_package_cache(self, loader):
        """Packages should be cached after first load."""
        package1 = loader.get_document_type("project_discovery")
        package2 = loader.get_document_type("project_discovery")

        assert package1 is package2

    def test_invalidate_cache(self, loader):
        """Cache invalidation should clear all caches."""
        package1 = loader.get_document_type("project_discovery")
        loader.invalidate_cache()
        package2 = loader.get_document_type("project_discovery")

        assert package1 is not package2


class TestListOperations:
    """Tests for list operations."""

    def test_list_document_types(self, loader):
        """Should list all document types."""
        doc_types = loader.list_document_types()

        assert "project_discovery" in doc_types
        assert "primary_implementation_plan" in doc_types

    def test_list_document_type_versions(self, loader):
        """Should list versions for a document type."""
        versions = loader.list_document_type_versions("project_discovery")

        assert "1.4.0" in versions
