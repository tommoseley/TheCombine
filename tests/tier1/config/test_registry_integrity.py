"""
Registry Integrity Tests (WS-REGISTRY-001).

Verifies that active_releases entries resolve to existing global canonical
artifacts via PackageLoader. No database, no network -- pure filesystem.
"""

import json
import pytest
from pathlib import Path

from app.config.package_loader import (
    PackageLoader,
    reset_package_loader,
)


CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "combine-config"
ACTIVE_RELEASES_PATH = CONFIG_PATH / "_active" / "active_releases.json"


@pytest.fixture
def loader():
    """Create a fresh PackageLoader."""
    reset_package_loader()
    return PackageLoader(CONFIG_PATH)


@pytest.fixture
def active_releases():
    """Load active_releases.json."""
    with open(ACTIVE_RELEASES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# =========================================================================
# Tests 1-4: work_package and work_statement resolve without error
# =========================================================================


class TestWorkPackageResolution:
    """Verify work_package task prompt and schema resolve from global paths."""

    def test_work_package_task_resolves(self, loader):
        """get_task('work_package') returns TaskPrompt with non-empty content."""
        task = loader.get_task("work_package")
        assert task.content, "work_package task prompt content is empty"
        assert task.task_id == "work_package"

    def test_work_package_schema_resolves(self, loader):
        """get_schema('work_package') returns StandaloneSchema with non-empty content."""
        schema = loader.get_schema("work_package")
        assert schema.content, "work_package schema content is empty"
        assert schema.schema_id == "work_package"


class TestWorkStatementResolution:
    """Verify work_statement task prompt and schema resolve from global paths."""

    def test_work_statement_task_resolves(self, loader):
        """get_task('work_statement') returns TaskPrompt with non-empty content."""
        task = loader.get_task("work_statement")
        assert task.content, "work_statement task prompt content is empty"
        assert task.task_id == "work_statement"

    def test_work_statement_schema_resolves(self, loader):
        """get_schema('work_statement') returns StandaloneSchema with non-empty content."""
        schema = loader.get_schema("work_statement")
        assert schema.content, "work_statement schema content is empty"
        assert schema.schema_id == "work_statement"


# =========================================================================
# Tests 5-6: Global content matches package-local content
# =========================================================================


class TestContentParity:
    """Global canonical artifacts must match their package-local sources."""

    def test_work_package_task_matches_package_local(self, loader):
        """Global task prompt for work_package matches package-local version."""
        global_task = loader.get_task("work_package")
        package = loader.get_document_type("work_package")
        local_content = package.get_task_prompt()
        assert local_content is not None, "package-local task prompt not found"
        assert global_task.content == local_content

    def test_work_statement_task_matches_package_local(self, loader):
        """Global task prompt for work_statement matches package-local version."""
        global_task = loader.get_task("work_statement")
        package = loader.get_document_type("work_statement")
        local_content = package.get_task_prompt()
        assert local_content is not None, "package-local task prompt not found"
        assert global_task.content == local_content


# =========================================================================
# Tests 7-8: All active entries have global directories
# =========================================================================


class TestActiveReleasesCompleteness:
    """Every active_releases entry should have a global canonical directory."""

    def test_all_active_tasks_have_global_directory(self, active_releases):
        """Every tasks entry in active_releases has a directory at
        combine-config/prompts/tasks/{id}/."""
        tasks = active_releases.get("tasks", {})
        missing = []
        for task_id, version in tasks.items():
            task_dir = CONFIG_PATH / "prompts" / "tasks" / task_id
            if not task_dir.is_dir():
                missing.append(f"{task_id}:{version}")
        assert not missing, (
            f"Tasks in active_releases with no global directory: {missing}"
        )

    def test_all_active_schemas_have_global_directory(self, active_releases):
        """Every schemas entry in active_releases has a directory at
        combine-config/schemas/{id}/."""
        schemas = active_releases.get("schemas", {})
        missing = []
        for schema_id, version in schemas.items():
            schema_dir = CONFIG_PATH / "schemas" / schema_id
            if not schema_dir.is_dir():
                missing.append(f"{schema_id}:{version}")
        assert not missing, (
            f"Schemas in active_releases with no global directory: {missing}"
        )
