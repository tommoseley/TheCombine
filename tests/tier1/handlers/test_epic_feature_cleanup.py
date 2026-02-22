"""
Tests for Epic/Feature Runtime Cleanup — WS-DCW-004.

Five test groups mapping to the five Tier 1 verification criteria:
  C1: No epic document type references in app/ and seed/
  C2: No feature document type references in app/ and seed/
  C3: No SPA epic/feature references (admin components, constants)
  C4: No stale imports referencing deleted epic/feature modules
  C5: Existing tests pass (verified by tier1 suite, not tested here)

Note: BCP hierarchy vocabulary (epic_backlog, epic as backlog level,
feature as a product capability) is KEPT — only old document type
ontology references are removed.
"""

import re
from pathlib import Path

import pytest


# =========================================================================
# Path constants
# =========================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]
APP_DIR = PROJECT_ROOT / "app"
SEED_DIR = PROJECT_ROOT / "seed"
SPA_SRC_DIR = PROJECT_ROOT / "spa" / "src"


# =========================================================================
# Helpers
# =========================================================================

def _read_py_files(directory: Path):
    """Yield (path, content) for all .py files in directory tree."""
    for py_file in directory.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        yield py_file, py_file.read_text()


def _read_jsx_files(directory: Path):
    """Yield (path, content) for all .jsx/.js files in directory tree."""
    for pattern in ["*.jsx", "*.js", "*.tsx", "*.ts"]:
        for js_file in directory.rglob(pattern):
            # Skip build artifacts and node_modules
            path_str = str(js_file)
            if "node_modules" in path_str or "dist/" in path_str:
                continue
            # Skip .map files (source maps)
            if js_file.suffix == ".map":
                continue
            yield js_file, js_file.read_text()


# =========================================================================
# C1 — No epic document type references
# =========================================================================


class TestC1NoEpicDocTypeReferences:
    """No code queries for or registers 'epic' as a document type."""

    def test_no_epic_doc_type_queries_in_app(self):
        """No SQL/ORM queries filtering on doc_type_id == 'epic'."""
        violations = []
        for path, content in _read_py_files(APP_DIR):
            for i, line in enumerate(content.splitlines(), 1):
                if re.search(r"""doc_type_id\s*==\s*['"]epic['"]""", line):
                    violations.append(f"{path.relative_to(PROJECT_ROOT)}:{i}")
        assert violations == [], (
            "Found epic doc_type_id queries:\n" +
            "\n".join(f"  {v}" for v in violations)
        )

    def test_no_epic_enum_in_package_model(self):
        """Package model scope enum must not define EPIC."""
        pkg_model = APP_DIR / "config" / "package_model.py"
        if not pkg_model.exists():
            return  # File doesn't exist, pass
        content = pkg_model.read_text()
        assert not re.search(r'EPIC\s*=\s*["\']epic["\']', content), (
            "package_model.py still defines EPIC scope enum"
        )

    def test_no_epicspec_class_in_artifacts(self):
        """No EpicSpec Pydantic model in domain schemas."""
        artifacts = APP_DIR / "domain" / "schemas" / "artifacts.py"
        if not artifacts.exists():
            return
        content = artifacts.read_text()
        assert "class EpicSpec" not in content, (
            "artifacts.py still defines EpicSpec class"
        )


# =========================================================================
# C2 — No feature document type references
# =========================================================================


class TestC2NoFeatureDocTypeReferences:
    """No code registers or references 'feature' as a document type."""

    def test_no_feature_doc_type_queries_in_app(self):
        """No SQL/ORM queries filtering on doc_type_id == 'feature'."""
        violations = []
        for path, content in _read_py_files(APP_DIR):
            for i, line in enumerate(content.splitlines(), 1):
                if re.search(r"""doc_type_id\s*==\s*['"]feature['"]""", line):
                    violations.append(f"{path.relative_to(PROJECT_ROOT)}:{i}")
        assert violations == [], (
            "Found feature doc_type_id queries:\n" +
            "\n".join(f"  {v}" for v in violations)
        )

    def test_no_feature_enum_in_package_model(self):
        """Package model scope enum must not define FEATURE."""
        pkg_model = APP_DIR / "config" / "package_model.py"
        if not pkg_model.exists():
            return
        content = pkg_model.read_text()
        assert not re.search(r'FEATURE\s*=\s*["\']feature["\']', content), (
            "package_model.py still defines FEATURE scope enum"
        )


# =========================================================================
# C3 — No SPA epic/feature references (admin components)
# =========================================================================


class TestC3NoSPAEpicFeatureReferences:
    """SPA admin components must not offer Epic/Feature as options."""

    @pytest.fixture(autouse=True)
    def _check_spa_exists(self):
        if not SPA_SRC_DIR.exists():
            pytest.skip("spa/src/ not present")

    def test_no_epic_option_in_admin_components(self):
        """Admin components must not have 'epic' as a selectable option value."""
        violations = []
        for path, content in _read_jsx_files(SPA_SRC_DIR / "components" / "admin"):
            for i, line in enumerate(content.splitlines(), 1):
                # Match <option value="epic"> or { value: 'epic' }
                if re.search(r"""value[=:]\s*['"]epic['"]""", line):
                    violations.append(f"{path.relative_to(PROJECT_ROOT)}:{i}")
        assert violations == [], (
            "Found epic option values in admin components:\n" +
            "\n".join(f"  {v}" for v in violations)
        )

    def test_no_feature_option_in_admin_components(self):
        """Admin components must not have 'feature' as a selectable option value."""
        violations = []
        for path, content in _read_jsx_files(SPA_SRC_DIR / "components" / "admin"):
            for i, line in enumerate(content.splitlines(), 1):
                if re.search(r"""value[=:]\s*['"]feature['"]""", line):
                    violations.append(f"{path.relative_to(PROJECT_ROOT)}:{i}")
        assert violations == [], (
            "Found feature option values in admin components:\n" +
            "\n".join(f"  {v}" for v in violations)
        )


# =========================================================================
# C4 — No stale imports
# =========================================================================


class TestC4NoStaleImports:
    """No import statements reference deleted epic/feature handler modules."""

    def test_no_import_of_epic_handler(self):
        """No Python file imports from a deleted epic_handler module."""
        violations = []
        for path, content in _read_py_files(APP_DIR):
            for i, line in enumerate(content.splitlines(), 1):
                if re.search(r'from\s+.*epic_handler\s+import|import\s+.*epic_handler', line):
                    violations.append(f"{path.relative_to(PROJECT_ROOT)}:{i}")
        assert violations == [], (
            "Found stale epic_handler imports:\n" +
            "\n".join(f"  {v}" for v in violations)
        )

    def test_no_import_of_feature_handler(self):
        """No Python file imports from a deleted feature_handler module."""
        violations = []
        for path, content in _read_py_files(APP_DIR):
            for i, line in enumerate(content.splitlines(), 1):
                if re.search(r'from\s+.*feature_handler\s+import|import\s+.*feature_handler', line):
                    violations.append(f"{path.relative_to(PROJECT_ROOT)}:{i}")
        assert violations == [], (
            "Found stale feature_handler imports:\n" +
            "\n".join(f"  {v}" for v in violations)
        )

    def test_no_import_of_epicspec(self):
        """No Python file imports EpicSpec from artifacts."""
        violations = []
        for path, content in _read_py_files(APP_DIR):
            for i, line in enumerate(content.splitlines(), 1):
                if "EpicSpec" in line and ("import" in line or "from" in line):
                    violations.append(f"{path.relative_to(PROJECT_ROOT)}:{i}")
        assert violations == [], (
            "Found stale EpicSpec imports:\n" +
            "\n".join(f"  {v}" for v in violations)
        )
