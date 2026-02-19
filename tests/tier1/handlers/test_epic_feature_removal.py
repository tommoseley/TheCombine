"""WS-ONTOLOGY-006: Guard tests ensuring Epic/Feature pipeline is fully removed.

These tests verify all 6 Tier 1 criteria:
  C1 - Epic doc type rejected (not in HANDLERS registry)
  C2 - Feature doc type rejected (not in HANDLERS registry)
  C3 - No Epic schemas in seed (not in INITIAL_DOCUMENT_TYPES)
  C4 - No Epic references in IPP/IPF handler code
  C5 - No Epic-specific API endpoints
  C6 - Regression guard (no epic type registrations in app/ or seed/)
"""

import inspect
import pathlib
import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
APP_DIR = PROJECT_ROOT / "app"
SEED_DIR = PROJECT_ROOT / "seed"
HANDLERS_DIR = APP_DIR / "domain" / "handlers"


# ===================================================================
# C1 — Epic doc type rejected
# ===================================================================

class TestC1EpicDocTypeRejected:
    """Attempting to get handler for 'epic' must fail."""

    def test_epic_not_in_handlers_registry(self):
        from app.domain.handlers.registry import HANDLERS
        assert "epic" not in HANDLERS, "Epic handler still registered"

    def test_epic_backlog_not_in_handlers_registry(self):
        from app.domain.handlers.registry import HANDLERS
        assert "epic_backlog" not in HANDLERS, "EpicBacklog handler still registered"

    def test_get_handler_rejects_epic(self):
        from app.domain.handlers.registry import get_handler
        from app.domain.handlers.exceptions import HandlerNotFoundError
        with pytest.raises(HandlerNotFoundError):
            get_handler("epic")

    def test_get_handler_rejects_epic_backlog(self):
        from app.domain.handlers.registry import get_handler
        from app.domain.handlers.exceptions import HandlerNotFoundError
        with pytest.raises(HandlerNotFoundError):
            get_handler("epic_backlog")


# ===================================================================
# C2 — Feature doc type rejected
# ===================================================================

class TestC2FeatureDocTypeRejected:
    """Attempting to get handler for 'feature' must fail."""

    def test_feature_not_in_handlers_registry(self):
        from app.domain.handlers.registry import HANDLERS
        assert "feature" not in HANDLERS, "Feature handler still registered"

    def test_get_handler_rejects_feature(self):
        from app.domain.handlers.registry import get_handler
        from app.domain.handlers.exceptions import HandlerNotFoundError
        with pytest.raises(HandlerNotFoundError):
            get_handler("feature")


# ===================================================================
# C3 — No Epic schemas in seed
# ===================================================================

class TestC3NoEpicSchemasInSeed:
    """No epic or feature entries in INITIAL_DOCUMENT_TYPES."""

    def test_no_epic_in_initial_document_types(self):
        from seed.registry.document_types import INITIAL_DOCUMENT_TYPES
        epic_ids = [
            d["doc_type_id"]
            for d in INITIAL_DOCUMENT_TYPES
            if d["doc_type_id"] in ("epic", "epic_backlog")
        ]
        assert epic_ids == [], f"Epic doc types still in seed: {epic_ids}"

    def test_no_feature_in_initial_document_types(self):
        from seed.registry.document_types import INITIAL_DOCUMENT_TYPES
        feature_ids = [
            d["doc_type_id"]
            for d in INITIAL_DOCUMENT_TYPES
            if d["doc_type_id"] == "feature"
        ]
        assert feature_ids == [], f"Feature doc type still in seed: {feature_ids}"


# ===================================================================
# C4 — No Epic references in IPP/IPF handler code
# ===================================================================

class TestC4NoEpicRefsInIPPIPF:
    """IPP and IPF handlers contain no epic/feature doc type references."""

    def test_ipp_handler_no_epic_refs(self):
        from app.domain.handlers import implementation_plan_primary_handler
        src = inspect.getsource(implementation_plan_primary_handler)
        # Check for epic as doc type concept — not as substring of other words
        assert "epic_candidates" not in src, "IPP handler still references epic_candidates"
        assert '"epic"' not in src, "IPP handler still references 'epic' doc type"

    def test_ipf_handler_no_epic_refs(self):
        from app.domain.handlers import implementation_plan_handler
        src = inspect.getsource(implementation_plan_handler)
        assert "epic" not in src.lower(), "IPF handler still references epic"
        assert "feature" not in src.lower(), "IPF handler still references feature"

    def test_ipp_handler_no_creates_children_epic(self):
        """IPP seed entry should not declare creates_children with epic."""
        from seed.registry.document_types import INITIAL_DOCUMENT_TYPES
        ipp = next(
            (d for d in INITIAL_DOCUMENT_TYPES if d["doc_type_id"] == "implementation_plan_primary"),
            None,
        )
        assert ipp is not None, "IPP not found in seed"
        children = ipp.get("creates_children", [])
        assert "epic" not in children, "IPP still creates epic children"

    def test_ipf_handler_no_creates_children_epic(self):
        """IPF seed entry should declare creates_children with work_package only."""
        from seed.registry.document_types import INITIAL_DOCUMENT_TYPES
        ipf = next(
            (d for d in INITIAL_DOCUMENT_TYPES if d["doc_type_id"] == "implementation_plan"),
            None,
        )
        assert ipf is not None, "IPF not found in seed"
        children = ipf.get("creates_children", [])
        assert "epic" not in children, "IPF still creates epic children"
        assert "feature" not in children, "IPF still creates feature children"


# ===================================================================
# C5 — No Epic-specific API endpoints
# ===================================================================

class TestC5NoEpicAPIEndpoints:
    """No epic-specific BFF, viewmodel, or route logic."""

    def test_no_epic_backlog_bff_module(self):
        bff_file = APP_DIR / "web" / "bff" / "epic_backlog_bff.py"
        assert not bff_file.exists(), f"Epic backlog BFF still exists: {bff_file}"

    def test_no_epic_backlog_viewmodel_module(self):
        vm_file = APP_DIR / "web" / "viewmodels" / "epic_backlog_vm.py"
        assert not vm_file.exists(), f"Epic backlog VM still exists: {vm_file}"

    def test_no_epic_handler_module(self):
        handler_file = HANDLERS_DIR / "epic_handler.py"
        assert not handler_file.exists(), f"Epic handler module still exists: {handler_file}"

    def test_no_feature_handler_module(self):
        handler_file = HANDLERS_DIR / "feature_handler.py"
        assert not handler_file.exists(), f"Feature handler module still exists: {handler_file}"

    def test_no_epic_backlog_handler_module(self):
        handler_file = HANDLERS_DIR / "epic_backlog_handler.py"
        assert not handler_file.exists(), f"Epic backlog handler module still exists: {handler_file}"


# ===================================================================
# C6 — Regression guard grep
# ===================================================================

class TestC6RegressionGuard:
    """Targeted checks: no epic/feature document type registrations remain.

    This guard focuses on the specific files where a doc type would be
    re-introduced (handler registry, seed data, handler files). It does NOT
    scan the entire codebase for the word "epic" — many subsystems (BCP
    pipeline, workflow scope, search, staleness) use "epic" as a backlog
    item hierarchy level or as DB queries against historical data.
    """

    def test_no_epic_handler_files(self):
        """No epic/feature handler .py files exist in handlers dir."""
        epic_files = list(HANDLERS_DIR.glob("epic*.py")) + list(HANDLERS_DIR.glob("feature*.py"))
        # Exclude __pycache__
        epic_files = [f for f in epic_files if "__pycache__" not in str(f)]
        assert epic_files == [], f"Epic/Feature handler files still exist: {epic_files}"

    def test_no_epic_in_handlers_dict(self):
        """Registry HANDLERS dict has no epic/feature keys."""
        registry_text = (HANDLERS_DIR / "registry.py").read_text()
        # Look for dict entries like "epic": ..., "feature": ..., "epic_backlog": ...
        import re
        handler_entries = re.findall(r'^\s*["\'](?:epic|feature|epic_backlog)["\']\s*:', registry_text, re.MULTILINE)
        assert handler_entries == [], f"HANDLERS dict still has epic entries: {handler_entries}"

    def test_no_epic_in_seed_doc_types(self):
        """Seed INITIAL_DOCUMENT_TYPES has no epic/feature doc_type_id."""
        seed_text = (SEED_DIR / "registry" / "document_types.py").read_text()
        import re
        # Match doc_type_id declarations for epic or feature
        matches = re.findall(r'"doc_type_id":\s*"(?:epic|feature)"', seed_text)
        assert matches == [], f"Seed still has epic/feature doc types: {matches}"

    def test_no_epic_handler_imports(self):
        """No imports of EpicHandler, FeatureHandler, or EpicBacklogHandler in registry."""
        registry_text = (HANDLERS_DIR / "registry.py").read_text()
        for cls in ["EpicHandler", "FeatureHandler", "EpicBacklogHandler"]:
            assert cls not in registry_text, f"Registry still imports {cls}"
