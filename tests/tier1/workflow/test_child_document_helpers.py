"""Tests for child_document_helpers pure functions (WS-CRAP-009).

Tests the 3 extracted pure functions:
1. unwrap_raw_envelope
2. inject_execution_id_into_lineage
3. build_children_event_payload
"""

import importlib
import importlib.util
import json

# Direct file import to avoid circular imports through app.domain.workflow.__init__
_spec = importlib.util.spec_from_file_location(
    "child_document_helpers_test",
    "app/domain/workflow/child_document_helpers.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

unwrap_raw_envelope = _mod.unwrap_raw_envelope
inject_execution_id_into_lineage = _mod.inject_execution_id_into_lineage
build_children_event_payload = _mod.build_children_event_payload


# ===================================================================
# 1. unwrap_raw_envelope
# ===================================================================

class TestUnwrapRawEnvelope:
    def test_no_raw_flag_returns_original(self):
        """Dict without raw=True is returned unchanged."""
        doc = {"title": "Hello", "content": {"sections": []}}
        result = unwrap_raw_envelope(doc)
        assert result is doc

    def test_raw_with_json_code_fences(self):
        """Raw envelope with ```json fences is unwrapped."""
        inner = {"work_packages": [{"id": "alpha"}]}
        envelope = {
            "raw": True,
            "content": f"```json\n{json.dumps(inner)}\n```",
        }
        result = unwrap_raw_envelope(envelope)
        assert result == inner

    def test_raw_without_code_fences(self):
        """Raw envelope with plain JSON string is parsed."""
        inner = {"sections": ["a", "b"]}
        envelope = {
            "raw": True,
            "content": json.dumps(inner),
        }
        result = unwrap_raw_envelope(envelope)
        assert result == inner

    def test_raw_with_invalid_json_returns_original(self):
        """Raw envelope with unparseable content returns original dict."""
        envelope = {
            "raw": True,
            "content": "not valid json {{{",
        }
        result = unwrap_raw_envelope(envelope)
        assert result is envelope

    def test_raw_with_non_string_content_returns_original(self):
        """Raw envelope where content is not a string returns original."""
        envelope = {
            "raw": True,
            "content": 12345,
        }
        result = unwrap_raw_envelope(envelope)
        assert result is envelope

    def test_non_dict_input_returns_original(self):
        """Non-dict input (e.g. list, string) is returned unchanged."""
        assert unwrap_raw_envelope([1, 2, 3]) == [1, 2, 3]
        assert unwrap_raw_envelope("hello") == "hello"
        assert unwrap_raw_envelope(None) is None


# ===================================================================
# 2. inject_execution_id_into_lineage
# ===================================================================

class TestInjectExecutionIdIntoLineage:
    def test_injects_into_spec_with_lineage(self):
        """execution_id is injected into _lineage metadata."""
        specs = [
            {
                "identifier": "alpha",
                "content": {
                    "_lineage": {"parent_execution_id": None},
                },
            }
        ]
        inject_execution_id_into_lineage(specs, "exec-001")
        assert specs[0]["content"]["_lineage"]["parent_execution_id"] == "exec-001"

    def test_skips_spec_without_lineage(self):
        """Specs without _lineage key are not modified."""
        specs = [
            {"identifier": "alpha", "content": {"data": "value"}},
        ]
        inject_execution_id_into_lineage(specs, "exec-002")
        assert "_lineage" not in specs[0]["content"]

    def test_noop_when_execution_id_is_none(self):
        """No-op when execution_id is None."""
        specs = [
            {
                "identifier": "alpha",
                "content": {
                    "_lineage": {"parent_execution_id": None},
                },
            }
        ]
        inject_execution_id_into_lineage(specs, None)
        assert specs[0]["content"]["_lineage"]["parent_execution_id"] is None


# ===================================================================
# 3. build_children_event_payload
# ===================================================================

class TestBuildChildrenEventPayload:
    def test_all_new_specs(self):
        """All specs are new → created populated, updated/superseded empty."""
        specs = [
            {"identifier": "alpha"},
            {"identifier": "beta"},
        ]
        result = build_children_event_payload(
            child_specs=specs,
            existing_ids=set(),
            spawned_ids={"alpha", "beta"},
        )
        assert result["created"] == ["alpha", "beta"]
        assert result["updated"] == []
        assert result["superseded"] == []

    def test_all_existing_specs(self):
        """All specs match existing → updated populated, created empty."""
        specs = [
            {"identifier": "alpha"},
            {"identifier": "beta"},
        ]
        result = build_children_event_payload(
            child_specs=specs,
            existing_ids={"alpha", "beta"},
            spawned_ids={"alpha", "beta"},
        )
        assert result["created"] == []
        assert result["updated"] == ["alpha", "beta"]
        assert result["superseded"] == []

    def test_mixed_create_update_supersede(self):
        """Mix of new, existing, and removed children."""
        specs = [
            {"identifier": "alpha"},  # existing → update
            {"identifier": "gamma"},  # new → create
        ]
        result = build_children_event_payload(
            child_specs=specs,
            existing_ids={"alpha", "beta"},
            spawned_ids={"alpha", "gamma"},
        )
        assert "gamma" in result["created"]
        assert "alpha" in result["updated"]
        assert "beta" in result["superseded"]

    def test_empty_specs(self):
        """Empty specs → all lists empty."""
        result = build_children_event_payload(
            child_specs=[],
            existing_ids=set(),
            spawned_ids=set(),
        )
        assert result == {"created": [], "updated": [], "superseded": []}
