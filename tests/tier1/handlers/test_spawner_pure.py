"""
Tests for spawner pure functions -- WS-CRAP-004.

Tests extracted pure functions: build_lineage, collect_seed_inputs,
assemble_spawn_receipt.
"""

from app.api.services.mech_handlers.spawner import (
    build_lineage,
    collect_seed_inputs,
    assemble_spawn_receipt,
)


# =========================================================================
# build_lineage
# =========================================================================


class TestBuildLineage:
    """Tests for build_lineage pure function."""

    def test_default_config(self):
        lineage = build_lineage({}, "parent_123", "op_456")
        assert lineage["spawned_from_execution_id"] == "parent_123"
        assert lineage["spawned_by_operation_id"] == "op_456"
        assert lineage["spawned_by_step_name"] == "Spawn Follow-on POW"

    def test_disable_spawned_from(self):
        config = {"set_spawned_from_execution_id": False}
        lineage = build_lineage(config, "parent_123", "op_456")
        assert lineage["spawned_from_execution_id"] is None
        assert lineage["spawned_by_operation_id"] == "op_456"

    def test_disable_spawned_by(self):
        config = {"set_spawned_by_operation_id": False}
        lineage = build_lineage(config, "parent_123", "op_456")
        assert lineage["spawned_from_execution_id"] == "parent_123"
        assert lineage["spawned_by_operation_id"] is None

    def test_both_disabled(self):
        config = {
            "set_spawned_from_execution_id": False,
            "set_spawned_by_operation_id": False,
        }
        lineage = build_lineage(config, "parent_123", "op_456")
        assert lineage["spawned_from_execution_id"] is None
        assert lineage["spawned_by_operation_id"] is None

    def test_both_enabled_explicitly(self):
        config = {
            "set_spawned_from_execution_id": True,
            "set_spawned_by_operation_id": True,
        }
        lineage = build_lineage(config, "p", "o")
        assert lineage["spawned_from_execution_id"] == "p"
        assert lineage["spawned_by_operation_id"] == "o"


# =========================================================================
# collect_seed_inputs
# =========================================================================


class TestCollectSeedInputs:
    """Tests for collect_seed_inputs pure function."""

    def test_collects_available_inputs(self):
        config = [
            {"from_artifact_id": "doc_a", "name": "discovery"},
            {"from_artifact_id": "doc_b", "name": "architecture"},
        ]
        available = {"doc_a", "doc_b", "doc_c"}
        result = collect_seed_inputs(config, available)
        assert len(result) == 2
        assert result[0] == {"name": "discovery", "artifact_id": "doc_a"}
        assert result[1] == {"name": "architecture", "artifact_id": "doc_b"}

    def test_filters_unavailable_inputs(self):
        config = [
            {"from_artifact_id": "doc_a", "name": "discovery"},
            {"from_artifact_id": "doc_missing", "name": "missing"},
        ]
        available = {"doc_a"}
        result = collect_seed_inputs(config, available)
        assert len(result) == 1
        assert result[0]["artifact_id"] == "doc_a"

    def test_name_defaults_to_artifact_id(self):
        config = [{"from_artifact_id": "doc_a"}]
        available = {"doc_a"}
        result = collect_seed_inputs(config, available)
        assert result[0]["name"] == "doc_a"

    def test_empty_config(self):
        result = collect_seed_inputs([], {"doc_a"})
        assert result == []

    def test_missing_artifact_id_skipped(self):
        config = [{"name": "no_artifact"}]
        available = {"anything"}
        result = collect_seed_inputs(config, available)
        assert result == []

    def test_empty_available_keys(self):
        config = [{"from_artifact_id": "doc_a", "name": "discovery"}]
        result = collect_seed_inputs(config, set())
        assert result == []


# =========================================================================
# assemble_spawn_receipt
# =========================================================================


class TestAssembleSpawnReceipt:
    """Tests for assemble_spawn_receipt pure function."""

    def test_basic_receipt(self):
        lineage = {"spawned_from_execution_id": "p1"}
        seed_inputs = [{"name": "doc", "artifact_id": "a1"}]
        receipt = assemble_spawn_receipt(
            "pow:test@1.0.0", "child_1", lineage, seed_inputs,
            spawned_at="2026-01-01T00:00:00Z",
        )
        assert receipt["schema_version"] == "spawn_receipt.v1"
        assert receipt["child_execution_id"] == "child_1"
        assert receipt["child_pow_ref"] == "pow:test@1.0.0"
        assert receipt["lineage"] == lineage
        assert receipt["seed_inputs"] == seed_inputs
        assert receipt["project_id"] is None
        assert receipt["project_event_written"] is False
        assert receipt["spawned_at"] == "2026-01-01T00:00:00Z"

    def test_with_project_id(self):
        receipt = assemble_spawn_receipt(
            "pow:test@1.0.0", "child_1", {}, [],
            project_id="proj_123",
            spawned_at="2026-01-01T00:00:00Z",
        )
        assert receipt["project_id"] == "proj_123"

    def test_with_project_event(self):
        receipt = assemble_spawn_receipt(
            "pow:test@1.0.0", "child_1", {}, [],
            write_project_event=True,
            spawned_at="2026-01-01T00:00:00Z",
        )
        assert receipt["project_event_written"] is True

    def test_auto_generated_timestamp(self):
        receipt = assemble_spawn_receipt("pow:test@1.0.0", "child_1", {}, [])
        assert receipt["spawned_at"] is not None
        assert "T" in receipt["spawned_at"]  # ISO format
