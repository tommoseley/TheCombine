"""Tier-1 CRAP score remediation tests for MechanicalOpsService.list_operations.

Covers the branching logic in list_operations (CC=18):
- ops_dir not existing
- active_mech_ops from attribute vs raw dict fallback
- directory iteration: skip non-dirs, skip underscore-prefixed
- active_version lookup: from active_releases, from scanning releases dir
- no active_version -> skip
- successful load with type found / type not found
- exception during load -> fallback summary with error
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

from app.api.services.mechanical_ops_service import (
    MechanicalOpsService,
    MechanicalOperation,
    OperationType,
)


# =========================================================================
# Helpers — fake PackageLoader and filesystem structures
# =========================================================================


def _make_fake_loader(
    config_path: Path,
    active_mech_ops: Optional[dict] = None,
    active_mech_ops_on_attr: bool = True,
) -> MagicMock:
    """Build a mock PackageLoader with controllable config_path and active_releases."""
    loader = MagicMock()
    loader.config_path = config_path

    active = MagicMock()
    if active_mech_ops_on_attr and active_mech_ops is not None:
        active.mechanical_ops = active_mech_ops
    else:
        # Simulate missing attribute — getattr returns {} or None
        active.mechanical_ops = {} if not active_mech_ops_on_attr else {}

    loader.get_active_releases.return_value = active
    return loader


class TestListOperationsOpsDir:
    """Tests for the ops_dir existence check."""

    def test_returns_empty_when_ops_dir_missing(self, tmp_path):
        """If mechanical_ops/ dir doesn't exist, return []."""
        config_path = tmp_path / "combine-config"
        config_path.mkdir()
        # Write a minimal registry so _ensure_types_loaded works
        registry_dir = config_path / "mechanical_ops" / "_registry"
        registry_dir.mkdir(parents=True)
        (registry_dir / "types.yaml").write_text("types: {}\ncategories: {}\n")

        # But then remove the mechanical_ops dir...
        # Actually, ops_dir = config_path / "mechanical_ops" exists because
        # _registry is inside. The check is ops_dir.exists(). Let's test
        # with no mechanical_ops at all.
        config_path2 = tmp_path / "combine-config2"
        config_path2.mkdir()
        # Provide no registry — _ensure_types_loaded will use empty fallback
        loader = _make_fake_loader(config_path2)

        svc = MechanicalOpsService(loader=loader)
        # Manually set caches to bypass _ensure_types_loaded's registry read
        svc._types_cache = {}
        svc._categories_cache = {}

        result = svc.list_operations()
        assert result == []


class TestListOperationsActiveMechOps:
    """Tests for the active_mech_ops resolution paths."""

    def test_active_mech_ops_from_attribute(self, tmp_path):
        """Active mech ops resolved from attribute (no fallback needed)."""
        config_path = tmp_path / "combine-config"
        ops_dir = config_path / "mechanical_ops"
        ops_dir.mkdir(parents=True)

        # Create an operation directory with a releases dir
        op_dir = ops_dir / "my_op"
        op_dir.mkdir()
        releases_dir = op_dir / "releases" / "1.0.0"
        releases_dir.mkdir(parents=True)

        loader = _make_fake_loader(
            config_path,
            active_mech_ops={"my_op": "1.0.0"},
            active_mech_ops_on_attr=True,
        )

        svc = MechanicalOpsService(loader=loader)
        svc._types_cache = {"some_type": OperationType(
            id="some_type", name="Some", description="desc",
            icon="icon", category="cat", config_schema={},
            inputs=[], outputs=[],
        )}
        svc._categories_cache = {}

        # _load_operation will be called — let's mock it
        fake_op = MechanicalOperation(
            id="my_op", version="1.0.0", type="some_type",
            name="My Op", description="My operation",
            config={}, metadata={"tags": ["test"]},
        )
        with patch.object(svc, "_load_operation", return_value=fake_op):
            result = svc.list_operations()

        assert len(result) == 1
        assert result[0]["op_id"] == "my_op"
        assert result[0]["name"] == "My Op"
        assert result[0]["type_name"] == "Some"
        assert result[0]["category"] == "cat"
        assert result[0]["active_version"] == "1.0.0"
        assert result[0]["tags"] == ["test"]

    def test_fallback_to_raw_json_when_attr_empty(self, tmp_path):
        """When attribute returns empty, fall back to active_releases.json."""
        config_path = tmp_path / "combine-config"
        ops_dir = config_path / "mechanical_ops"
        ops_dir.mkdir(parents=True)

        # Write active_releases.json with mechanical_ops
        active_dir = config_path / "_active"
        active_dir.mkdir(parents=True)
        (active_dir / "active_releases.json").write_text(
            json.dumps({"mechanical_ops": {"op_a": "2.0.0"}}),
            encoding="utf-8",
        )

        # Create op_a directory
        op_a_dir = ops_dir / "op_a"
        op_a_dir.mkdir()

        loader = _make_fake_loader(
            config_path,
            active_mech_ops={},
            active_mech_ops_on_attr=True,
        )

        svc = MechanicalOpsService(loader=loader)
        svc._types_cache = {}
        svc._categories_cache = {}

        fake_op = MechanicalOperation(
            id="op_a", version="2.0.0", type="type_x",
            name="Op A", description="desc",
            config={}, metadata={},
        )
        with patch.object(svc, "_load_operation", return_value=fake_op):
            result = svc.list_operations()

        assert len(result) == 1
        assert result[0]["op_id"] == "op_a"
        assert result[0]["active_version"] == "2.0.0"

    def test_fallback_json_file_not_exist(self, tmp_path):
        """When attr empty and active_releases.json doesn't exist, no crash."""
        config_path = tmp_path / "combine-config"
        ops_dir = config_path / "mechanical_ops"
        ops_dir.mkdir(parents=True)

        # Create an operation with a releases dir containing a version
        op_dir = ops_dir / "op_b"
        op_dir.mkdir()
        releases_dir = op_dir / "releases" / "1.0.0"
        releases_dir.mkdir(parents=True)

        loader = _make_fake_loader(
            config_path,
            active_mech_ops={},
            active_mech_ops_on_attr=True,
        )

        svc = MechanicalOpsService(loader=loader)
        svc._types_cache = {}
        svc._categories_cache = {}

        # No active_releases.json, but version found via releases dir scan
        fake_op = MechanicalOperation(
            id="op_b", version="1.0.0", type="type_y",
            name="Op B", description="desc",
            config={}, metadata={},
        )
        with patch.object(svc, "_load_operation", return_value=fake_op):
            result = svc.list_operations()

        assert len(result) == 1
        assert result[0]["op_id"] == "op_b"
        assert result[0]["active_version"] == "1.0.0"

    def test_fallback_json_parse_error(self, tmp_path):
        """When active_releases.json is malformed, exception is swallowed."""
        config_path = tmp_path / "combine-config"
        ops_dir = config_path / "mechanical_ops"
        ops_dir.mkdir(parents=True)

        active_dir = config_path / "_active"
        active_dir.mkdir(parents=True)
        (active_dir / "active_releases.json").write_text(
            "NOT VALID JSON", encoding="utf-8",
        )

        # Op with release dir so it can still find a version
        op_dir = ops_dir / "op_c"
        op_dir.mkdir()
        releases_dir = op_dir / "releases" / "0.1.0"
        releases_dir.mkdir(parents=True)

        loader = _make_fake_loader(
            config_path,
            active_mech_ops={},
            active_mech_ops_on_attr=True,
        )

        svc = MechanicalOpsService(loader=loader)
        svc._types_cache = {}
        svc._categories_cache = {}

        fake_op = MechanicalOperation(
            id="op_c", version="0.1.0", type="type_z",
            name="Op C", description="desc",
            config={}, metadata={},
        )
        with patch.object(svc, "_load_operation", return_value=fake_op):
            result = svc.list_operations()

        assert len(result) == 1


class TestListOperationsDirectoryIteration:
    """Tests for directory filtering logic."""

    def test_skips_non_directory_entries(self, tmp_path):
        """Files in ops_dir are skipped."""
        config_path = tmp_path / "combine-config"
        ops_dir = config_path / "mechanical_ops"
        ops_dir.mkdir(parents=True)

        # Create a file (not a dir)
        (ops_dir / "some_file.txt").write_text("hi")

        loader = _make_fake_loader(
            config_path, active_mech_ops={}, active_mech_ops_on_attr=True,
        )
        svc = MechanicalOpsService(loader=loader)
        svc._types_cache = {}
        svc._categories_cache = {}

        result = svc.list_operations()
        assert result == []

    def test_skips_underscore_prefixed_dirs(self, tmp_path):
        """Directories starting with _ are skipped (like _registry)."""
        config_path = tmp_path / "combine-config"
        ops_dir = config_path / "mechanical_ops"
        ops_dir.mkdir(parents=True)

        # Create _registry dir — should be skipped
        (ops_dir / "_registry").mkdir()
        (ops_dir / "_hidden").mkdir()

        loader = _make_fake_loader(
            config_path, active_mech_ops={}, active_mech_ops_on_attr=True,
        )
        svc = MechanicalOpsService(loader=loader)
        svc._types_cache = {}
        svc._categories_cache = {}

        result = svc.list_operations()
        assert result == []


class TestListOperationsVersionResolution:
    """Tests for active_version resolution."""

    def test_no_active_version_and_no_releases_skips(self, tmp_path):
        """If no active_version and no releases dir, op is skipped."""
        config_path = tmp_path / "combine-config"
        ops_dir = config_path / "mechanical_ops"
        ops_dir.mkdir(parents=True)

        # Create op dir with NO releases
        (ops_dir / "orphan_op").mkdir()

        loader = _make_fake_loader(
            config_path, active_mech_ops={}, active_mech_ops_on_attr=True,
        )
        svc = MechanicalOpsService(loader=loader)
        svc._types_cache = {}
        svc._categories_cache = {}

        result = svc.list_operations()
        assert result == []

    def test_no_active_version_but_empty_releases_skips(self, tmp_path):
        """If releases dir exists but has no version subdirs, op is skipped."""
        config_path = tmp_path / "combine-config"
        ops_dir = config_path / "mechanical_ops"
        ops_dir.mkdir(parents=True)

        op_dir = ops_dir / "empty_op"
        op_dir.mkdir()
        (op_dir / "releases").mkdir()

        loader = _make_fake_loader(
            config_path, active_mech_ops={}, active_mech_ops_on_attr=True,
        )
        svc = MechanicalOpsService(loader=loader)
        svc._types_cache = {}
        svc._categories_cache = {}

        result = svc.list_operations()
        assert result == []

    def test_discovers_latest_version_from_releases(self, tmp_path):
        """When no active version, picks last sorted version from releases/."""
        config_path = tmp_path / "combine-config"
        ops_dir = config_path / "mechanical_ops"
        ops_dir.mkdir(parents=True)

        op_dir = ops_dir / "multi_ver"
        (op_dir / "releases" / "1.0.0").mkdir(parents=True)
        (op_dir / "releases" / "2.0.0").mkdir(parents=True)

        loader = _make_fake_loader(
            config_path, active_mech_ops={}, active_mech_ops_on_attr=True,
        )
        svc = MechanicalOpsService(loader=loader)
        svc._types_cache = {}
        svc._categories_cache = {}

        fake_op = MechanicalOperation(
            id="multi_ver", version="2.0.0", type="t",
            name="Multi", description="d", config={}, metadata={},
        )
        with patch.object(svc, "_load_operation", return_value=fake_op):
            result = svc.list_operations()

        assert len(result) == 1
        assert result[0]["active_version"] == "2.0.0"


class TestListOperationsLoadSuccess:
    """Tests for successful operation loading."""

    def test_type_found_populates_type_name_and_category(self, tmp_path):
        """When op type is in the cache, type_name and category come from it."""
        config_path = tmp_path / "combine-config"
        ops_dir = config_path / "mechanical_ops"
        ops_dir.mkdir(parents=True)
        (ops_dir / "op1").mkdir()

        loader = _make_fake_loader(
            config_path, active_mech_ops={"op1": "1.0.0"},
        )
        svc = MechanicalOpsService(loader=loader)
        svc._types_cache = {
            "transform": OperationType(
                id="transform", name="Transform", description="",
                icon="", category="data", config_schema={},
                inputs=[], outputs=[],
            ),
        }
        svc._categories_cache = {}

        fake_op = MechanicalOperation(
            id="op1", version="1.0.0", type="transform",
            name="Op1", description="desc", config={}, metadata={},
        )
        with patch.object(svc, "_load_operation", return_value=fake_op):
            result = svc.list_operations()

        assert result[0]["type_name"] == "Transform"
        assert result[0]["category"] == "data"

    def test_type_not_found_falls_back(self, tmp_path):
        """When op type is NOT in cache, type_name=None, category=None."""
        config_path = tmp_path / "combine-config"
        ops_dir = config_path / "mechanical_ops"
        ops_dir.mkdir(parents=True)
        (ops_dir / "op2").mkdir()

        loader = _make_fake_loader(
            config_path, active_mech_ops={"op2": "1.0.0"},
        )
        svc = MechanicalOpsService(loader=loader)
        svc._types_cache = {}  # No types loaded
        svc._categories_cache = {}

        fake_op = MechanicalOperation(
            id="op2", version="1.0.0", type="unknown_type",
            name="Op2", description="desc", config={}, metadata={},
        )
        with patch.object(svc, "_load_operation", return_value=fake_op):
            result = svc.list_operations()

        # build_operation_summary uses `type_name or op_type` when None
        assert result[0]["type_name"] == "unknown_type"
        assert result[0]["category"] == "uncategorized"


class TestListOperationsLoadFailure:
    """Tests for exception handling during operation load."""

    def test_exception_produces_error_summary(self, tmp_path):
        """When _load_operation raises, an error summary is appended."""
        config_path = tmp_path / "combine-config"
        ops_dir = config_path / "mechanical_ops"
        ops_dir.mkdir(parents=True)
        (ops_dir / "bad_op").mkdir()

        loader = _make_fake_loader(
            config_path, active_mech_ops={"bad_op": "1.0.0"},
        )
        svc = MechanicalOpsService(loader=loader)
        svc._types_cache = {}
        svc._categories_cache = {}

        with patch.object(
            svc, "_load_operation", side_effect=RuntimeError("corrupt yaml"),
        ):
            result = svc.list_operations()

        assert len(result) == 1
        s = result[0]
        assert s["op_id"] == "bad_op"
        assert s["name"] == "bad_op"
        assert s["error"] == "corrupt yaml"
        assert s["category"] == "uncategorized"
        assert s["tags"] == []

    def test_mixed_success_and_failure(self, tmp_path):
        """Some ops load, some fail — both appear in results."""
        config_path = tmp_path / "combine-config"
        ops_dir = config_path / "mechanical_ops"
        ops_dir.mkdir(parents=True)
        (ops_dir / "good_op").mkdir()
        (ops_dir / "bad_op").mkdir()

        loader = _make_fake_loader(
            config_path,
            active_mech_ops={"good_op": "1.0.0", "bad_op": "1.0.0"},
        )
        svc = MechanicalOpsService(loader=loader)
        svc._types_cache = {}
        svc._categories_cache = {}

        good_op = MechanicalOperation(
            id="good_op", version="1.0.0", type="t",
            name="Good", description="works", config={}, metadata={},
        )

        def side_effect(op_id, version):
            if op_id == "good_op":
                return good_op
            raise RuntimeError("broken")

        with patch.object(svc, "_load_operation", side_effect=side_effect):
            result = svc.list_operations()

        assert len(result) == 2
        ids = {r["op_id"] for r in result}
        assert ids == {"good_op", "bad_op"}
        errors = [r for r in result if "error" in r]
        assert len(errors) == 1
        assert errors[0]["op_id"] == "bad_op"
