"""
Tests for Seed Cleanup — WS-DCW-005.

Six test groups mapping to the six Tier 1 verification criteria:
  C1: No runtime seed/workflows/ loading references
  C2: Stale ops scripts cleaned
  C3: All document types loadable from combine-config
  C4: No broken imports from seed path changes
  C5: Split-brain guard (no seed workflow without combine-config counterpart)
  C6: Existing tests pass (verified by tier1 suite, not tested here)
"""

import json
import re
from pathlib import Path


# =========================================================================
# Path constants
# =========================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]
APP_DIR = PROJECT_ROOT / "app"
OPS_DIR = PROJECT_ROOT / "ops"
SEED_WORKFLOWS_DIR = PROJECT_ROOT / "seed" / "workflows"
CC_WORKFLOWS_DIR = PROJECT_ROOT / "combine-config" / "workflows"
ACTIVE_RELEASES_PATH = (
    PROJECT_ROOT / "combine-config" / "_active" / "active_releases.json"
)


# =========================================================================
# Helpers
# =========================================================================

def _read_py_files(directory: Path):
    """Yield (path, content) for all .py files in directory tree."""
    for py_file in directory.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        yield py_file, py_file.read_text()


# =========================================================================
# C1 — No runtime seed/workflows/ loading references
# =========================================================================


class TestC1NoRuntimeSeedWorkflowsLoading:
    """No runtime code references seed/workflows/ for workflow loading."""

    def test_no_seed_workflows_string_in_runtime_code(self):
        """No Python file in app/ contains the string 'seed/workflows/' in code or comments."""
        violations = []
        for path, content in _read_py_files(APP_DIR):
            for i, line in enumerate(content.splitlines(), 1):
                if "seed/workflows/" in line:
                    violations.append(
                        f"{path.relative_to(PROJECT_ROOT)}:{i}: {line.strip()}"
                    )
        assert violations == [], (
            "Found seed/workflows/ references in runtime code:\n" +
            "\n".join(f"  {v}" for v in violations)
        )

    def test_no_seed_workflows_function_names(self):
        """No function or variable in app/ named *seed_workflow*."""
        violations = []
        for path, content in _read_py_files(APP_DIR):
            for i, line in enumerate(content.splitlines(), 1):
                if re.search(r'seed_workflow', line):
                    violations.append(
                        f"{path.relative_to(PROJECT_ROOT)}:{i}: {line.strip()}"
                    )
        assert violations == [], (
            "Found seed_workflow naming in runtime code:\n" +
            "\n".join(f"  {v}" for v in violations)
        )


# =========================================================================
# C2 — Stale ops scripts cleaned
# =========================================================================


class TestC2StaleOpsScriptsCleaned:
    """Stale seed scripts deleted or clearly deprecated."""

    def test_seed_data_py_deleted(self):
        """ops/db/seed_data.py must not exist (stale)."""
        stale_path = OPS_DIR / "db" / "seed_data.py"
        assert not stale_path.exists(), (
            f"Stale script still exists: {stale_path.relative_to(PROJECT_ROOT)}"
        )

    def test_seed_acceptance_config_py_deleted(self):
        """ops/db/seed_acceptance_config.py must not exist (stale)."""
        stale_path = OPS_DIR / "db" / "seed_acceptance_config.py"
        assert not stale_path.exists(), (
            f"Stale script still exists: {stale_path.relative_to(PROJECT_ROOT)}"
        )

    def test_db_migrate_no_stale_seed_references(self):
        """db_migrate.sh must not reference deleted seed scripts."""
        migrate_path = OPS_DIR / "scripts" / "db_migrate.sh"
        if not migrate_path.exists():
            return  # Script doesn't exist, pass
        content = migrate_path.read_text()
        assert "seed_data.py" not in content, (
            "db_migrate.sh still references seed_data.py"
        )
        assert "seed_acceptance_config.py" not in content, (
            "db_migrate.sh still references seed_acceptance_config.py"
        )


# =========================================================================
# C3 — All document types loadable from combine-config
# =========================================================================


class TestC3AllDocTypesLoadableFromCombineConfig:
    """All workflow document types are registered in combine-config active_releases."""

    def test_active_releases_exists(self):
        assert ACTIVE_RELEASES_PATH.exists(), (
            "combine-config/_active/active_releases.json not found"
        )

    def test_core_document_types_in_active_releases(self):
        """All core document types have entries in active_releases.json."""
        with open(ACTIVE_RELEASES_PATH) as f:
            active = json.load(f)
        doc_types = active.get("document_types", {})
        for dt in [
            "concierge_intake",
            "project_discovery",
            "technical_architecture",
            "implementation_plan",
            "work_package",
            "work_statement",
        ]:
            assert dt in doc_types, (
                f"Document type '{dt}' not in active_releases document_types"
            )

    def test_core_workflows_in_active_releases(self):
        """All core workflows have entries in active_releases.json."""
        with open(ACTIVE_RELEASES_PATH) as f:
            active = json.load(f)
        workflows = active.get("workflows", {})
        for wf in [
            "software_product_development",
            "concierge_intake",
            "project_discovery",
            "technical_architecture",
            "implementation_plan",
            "work_package",
            "work_statement",
        ]:
            assert wf in workflows, (
                f"Workflow '{wf}' not in active_releases workflows"
            )

    def test_each_workflow_definition_exists_on_disk(self):
        """Every workflow in active_releases.json has a definition.json on disk."""
        with open(ACTIVE_RELEASES_PATH) as f:
            active = json.load(f)
        missing = []
        for wf_id, version in active.get("workflows", {}).items():
            def_path = CC_WORKFLOWS_DIR / wf_id / "releases" / version / "definition.json"
            if not def_path.exists():
                missing.append(f"{wf_id} v{version} -> {def_path}")
        assert missing == [], (
            "Workflow definitions missing from disk:\n" +
            "\n".join(f"  {m}" for m in missing)
        )


# =========================================================================
# C4 — No broken imports
# =========================================================================


class TestC4NoBrokenImports:
    """No import statements reference deleted seed modules."""

    def test_no_imports_of_seed_data_module(self):
        """No Python file in app/ or ops/ imports from seed_data."""
        violations = []
        for search_dir in [APP_DIR, OPS_DIR]:
            if not search_dir.exists():
                continue
            for path, content in _read_py_files(search_dir):
                for i, line in enumerate(content.splitlines(), 1):
                    if re.search(r'from\s+.*seed_data\s+import|import\s+.*seed_data', line):
                        violations.append(
                            f"{path.relative_to(PROJECT_ROOT)}:{i}"
                        )
        assert violations == [], (
            "Found stale seed_data imports:\n" +
            "\n".join(f"  {v}" for v in violations)
        )

    def test_no_imports_of_seed_acceptance_config(self):
        """No Python file in app/ or ops/ imports from seed_acceptance_config."""
        violations = []
        for search_dir in [APP_DIR, OPS_DIR]:
            if not search_dir.exists():
                continue
            for path, content in _read_py_files(search_dir):
                for i, line in enumerate(content.splitlines(), 1):
                    if re.search(
                        r'from\s+.*seed_acceptance_config\s+import|import\s+.*seed_acceptance_config',
                        line,
                    ):
                        violations.append(
                            f"{path.relative_to(PROJECT_ROOT)}:{i}"
                        )
        assert violations == [], (
            "Found stale seed_acceptance_config imports:\n" +
            "\n".join(f"  {v}" for v in violations)
        )


# =========================================================================
# C5 — Split-brain guard
# =========================================================================


class TestC5SplitBrainGuard:
    """No workflow in seed/ without a counterpart in combine-config/."""

    def test_no_seed_only_workflows(self):
        """Every workflow in seed/workflows/ must have a combine-config counterpart."""
        seed_wf_names = {
            f.stem.rsplit(".", 1)[0]
            for f in SEED_WORKFLOWS_DIR.glob("*.json")
            if f.is_file()
        }
        cc_wf_names = {
            d.name
            for d in CC_WORKFLOWS_DIR.iterdir()
            if d.is_dir() and not d.name.startswith("_")
        }
        seed_only = seed_wf_names - cc_wf_names
        assert not seed_only, (
            f"Workflows in seed/ but not combine-config/: {seed_only}"
        )
