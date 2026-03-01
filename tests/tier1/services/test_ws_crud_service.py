"""
Tier-1 tests for ws_crud_service.py.

Pure in-memory, no DB, no LLM.
Tests WS CRUD pure functions: ID generation, order keys, plane separation,
stabilization, and ws_index manipulation.

WS-WB-006.
"""


from app.domain.services.ws_crud_service import (
    WS_BLOCKED_IN_UPDATE,
    WP_BLOCKED_IN_UPDATE,
    WS_REQUIRED_FOR_STABILIZE,
    generate_ws_id,
    generate_order_key,
    build_new_ws,
    validate_ws_update_fields,
    validate_wp_update_fields,
    validate_stabilization,
    add_ws_to_wp_index,
    reorder_ws_index,
)


# ===========================================================================
# generate_ws_id
# ===========================================================================

class TestGenerateWsId:

    def test_basic_wp_id(self):
        result = generate_ws_id("wp_wb_001", 1)
        assert result == "WS-WB-001"

    def test_sequence_two(self):
        result = generate_ws_id("wp_wb_001", 2)
        assert result == "WS-WB-002"

    def test_high_sequence(self):
        result = generate_ws_id("wp_wb_001", 15)
        assert result == "WS-WB-015"

    def test_multi_segment_prefix(self):
        result = generate_ws_id("wp_pipeline_003", 5)
        assert result == "WS-PIPELINE-005"

    def test_uppercase_output(self):
        result = generate_ws_id("wp_crap_001", 1)
        assert result == "WS-CRAP-001"

    def test_prefix_is_uppercase(self):
        result = generate_ws_id("wp_wb_001", 1)
        assert "WS-" in result
        # Verify the prefix part is uppercase
        parts = result.split("-")
        assert parts[0] == "WS"
        assert parts[1] == "WB"


# ===========================================================================
# generate_order_key
# ===========================================================================

class TestGenerateOrderKey:

    def test_empty_list_returns_a0(self):
        assert generate_order_key([]) == "a0"

    def test_after_a0_returns_a1(self):
        assert generate_order_key(["a0"]) == "a1"

    def test_after_a1_returns_a2(self):
        assert generate_order_key(["a0", "a1"]) == "a2"

    def test_after_a9_rolls_to_b0(self):
        keys = [f"a{i}" for i in range(10)]
        assert generate_order_key(keys) == "b0"

    def test_after_b9_rolls_to_c0(self):
        keys = [f"a{i}" for i in range(10)] + [f"b{i}" for i in range(10)]
        assert generate_order_key(keys) == "c0"

    def test_unsorted_input_finds_highest(self):
        """Even with unsorted input, should find the max key."""
        assert generate_order_key(["a2", "a0", "a1"]) == "a3"

    def test_single_key_a5(self):
        assert generate_order_key(["a5"]) == "a6"


# ===========================================================================
# build_new_ws
# ===========================================================================

class TestBuildNewWs:

    def test_state_is_draft(self):
        ws = build_new_ws("wp_wb_001", "WS-WB-001", "a0", {})
        assert ws["state"] == "DRAFT"

    def test_revision_is_one(self):
        ws = build_new_ws("wp_wb_001", "WS-WB-001", "a0", {})
        assert ws["revision"] == 1

    def test_ws_id_set(self):
        ws = build_new_ws("wp_wb_001", "WS-WB-001", "a0", {})
        assert ws["ws_id"] == "WS-WB-001"

    def test_parent_wp_id_set(self):
        ws = build_new_ws("wp_wb_001", "WS-WB-001", "a0", {})
        assert ws["parent_wp_id"] == "wp_wb_001"

    def test_order_key_set(self):
        ws = build_new_ws("wp_wb_001", "WS-WB-001", "a0", {})
        assert ws["order_key"] == "a0"

    def test_content_fields_populated(self):
        content = {
            "title": "My WS",
            "objective": "Do something",
            "procedure": ["Step 1", "Step 2"],
            "verification_criteria": ["Check A"],
        }
        ws = build_new_ws("wp_wb_001", "WS-WB-001", "a0", content)
        assert ws["title"] == "My WS"
        assert ws["objective"] == "Do something"
        assert ws["procedure"] == ["Step 1", "Step 2"]
        assert ws["verification_criteria"] == ["Check A"]

    def test_missing_content_defaults_to_empty(self):
        ws = build_new_ws("wp_wb_001", "WS-WB-001", "a0", {})
        assert ws["title"] == ""
        assert ws["objective"] == ""
        assert ws["scope_in"] == []
        assert ws["scope_out"] == []
        assert ws["allowed_paths"] == []
        assert ws["procedure"] == []
        assert ws["verification_criteria"] == []
        assert ws["prohibited_actions"] == []
        assert ws["governance_pins"] == {}


# ===========================================================================
# validate_ws_update_fields (plane separation)
# ===========================================================================

class TestValidateWsUpdateFields:

    def test_valid_ws_fields_no_errors(self):
        update = {"title": "New title", "objective": "Updated objective"}
        errors = validate_ws_update_fields(update)
        assert errors == []

    def test_ws_index_rejected(self):
        update = {"ws_index": []}
        errors = validate_ws_update_fields(update)
        assert len(errors) == 1
        assert "ws_index" in errors[0]

    def test_change_summary_rejected(self):
        update = {"change_summary": "something"}
        errors = validate_ws_update_fields(update)
        assert len(errors) == 1
        assert "change_summary" in errors[0]

    def test_multiple_blocked_fields(self):
        update = {
            "ws_index": [],
            "ws_total": 5,
            "dependencies": [],
        }
        errors = validate_ws_update_fields(update)
        assert len(errors) == 3

    def test_all_blocked_fields_covered(self):
        """Every field in WS_BLOCKED_IN_UPDATE should produce an error."""
        for field in WS_BLOCKED_IN_UPDATE:
            errors = validate_ws_update_fields({field: "test"})
            assert len(errors) == 1, f"Field '{field}' was not blocked"

    def test_mixed_valid_and_blocked(self):
        update = {"title": "OK", "ws_total": 5}
        errors = validate_ws_update_fields(update)
        assert len(errors) == 1
        assert "ws_total" in errors[0]


# ===========================================================================
# validate_wp_update_fields (plane separation)
# ===========================================================================

class TestValidateWpUpdateFields:

    def test_valid_wp_fields_no_errors(self):
        update = {"title": "New WP title", "rationale": "Updated rationale"}
        errors = validate_wp_update_fields(update)
        assert errors == []

    def test_objective_rejected(self):
        update = {"objective": "WS objective shouldn't be here"}
        errors = validate_wp_update_fields(update)
        assert len(errors) == 1
        assert "objective" in errors[0]

    def test_procedure_rejected(self):
        update = {"procedure": ["Step 1"]}
        errors = validate_wp_update_fields(update)
        assert len(errors) == 1
        assert "procedure" in errors[0]

    def test_multiple_ws_fields_rejected(self):
        update = {
            "objective": "WS field",
            "procedure": [],
            "verification_criteria": [],
        }
        errors = validate_wp_update_fields(update)
        assert len(errors) == 3

    def test_all_blocked_fields_covered(self):
        """Every field in WP_BLOCKED_IN_UPDATE should produce an error."""
        for field in WP_BLOCKED_IN_UPDATE:
            errors = validate_wp_update_fields({field: "test"})
            assert len(errors) == 1, f"Field '{field}' was not blocked"

    def test_mixed_valid_and_blocked(self):
        update = {"title": "OK", "allowed_paths": ["app/"]}
        errors = validate_wp_update_fields(update)
        assert len(errors) == 1
        assert "allowed_paths" in errors[0]


# ===========================================================================
# validate_stabilization
# ===========================================================================

class TestValidateStabilization:

    def test_all_required_present_no_errors(self):
        ws = {
            "title": "My WS",
            "objective": "Do something",
            "procedure": ["Step 1"],
            "verification_criteria": ["Check A"],
        }
        errors = validate_stabilization(ws)
        assert errors == []

    def test_missing_title(self):
        ws = {
            "objective": "Do something",
            "procedure": ["Step 1"],
            "verification_criteria": ["Check A"],
        }
        errors = validate_stabilization(ws)
        assert len(errors) == 1
        assert "title" in errors[0]

    def test_empty_title(self):
        ws = {
            "title": "",
            "objective": "Do something",
            "procedure": ["Step 1"],
            "verification_criteria": ["Check A"],
        }
        errors = validate_stabilization(ws)
        assert len(errors) == 1
        assert "title" in errors[0]

    def test_empty_procedure_list(self):
        ws = {
            "title": "My WS",
            "objective": "Do something",
            "procedure": [],
            "verification_criteria": ["Check A"],
        }
        errors = validate_stabilization(ws)
        assert len(errors) == 1
        assert "procedure" in errors[0]

    def test_multiple_missing_fields(self):
        ws = {}
        errors = validate_stabilization(ws)
        assert len(errors) == len(WS_REQUIRED_FOR_STABILIZE)

    def test_none_value_treated_as_missing(self):
        ws = {
            "title": None,
            "objective": "OK",
            "procedure": ["Step"],
            "verification_criteria": ["Check"],
        }
        errors = validate_stabilization(ws)
        assert len(errors) == 1
        assert "title" in errors[0]


# ===========================================================================
# add_ws_to_wp_index
# ===========================================================================

class TestAddWsToWpIndex:

    def test_add_to_empty_index(self):
        wp = {}
        result = add_ws_to_wp_index(wp, "WS-WB-001", "a0")
        assert len(result["ws_index"]) == 1
        assert result["ws_index"][0] == {"ws_id": "WS-WB-001", "order_key": "a0"}

    def test_add_second_ws(self):
        wp = {"ws_index": [{"ws_id": "WS-WB-001", "order_key": "a0"}]}
        result = add_ws_to_wp_index(wp, "WS-WB-002", "a1")
        assert len(result["ws_index"]) == 2
        assert result["ws_index"][1]["ws_id"] == "WS-WB-002"

    def test_duplicate_ws_id_ignored(self):
        wp = {"ws_index": [{"ws_id": "WS-WB-001", "order_key": "a0"}]}
        result = add_ws_to_wp_index(wp, "WS-WB-001", "a0")
        assert len(result["ws_index"]) == 1

    def test_maintains_order_by_key(self):
        wp = {"ws_index": [{"ws_id": "WS-WB-002", "order_key": "a1"}]}
        result = add_ws_to_wp_index(wp, "WS-WB-001", "a0")
        assert result["ws_index"][0]["ws_id"] == "WS-WB-001"
        assert result["ws_index"][1]["ws_id"] == "WS-WB-002"


# ===========================================================================
# reorder_ws_index
# ===========================================================================

class TestReorderWsIndex:

    def test_reorder_two_items(self):
        wp = {
            "ws_index": [
                {"ws_id": "WS-WB-001", "order_key": "a0"},
                {"ws_id": "WS-WB-002", "order_key": "a1"},
            ]
        }
        new_order = [
            {"ws_id": "WS-WB-002", "order_key": "a0"},
            {"ws_id": "WS-WB-001", "order_key": "a1"},
        ]
        result = reorder_ws_index(wp, new_order)
        assert result["ws_index"][0]["ws_id"] == "WS-WB-002"
        assert result["ws_index"][1]["ws_id"] == "WS-WB-001"

    def test_reorder_sorts_by_order_key(self):
        new_order = [
            {"ws_id": "WS-WB-003", "order_key": "b0"},
            {"ws_id": "WS-WB-001", "order_key": "a0"},
            {"ws_id": "WS-WB-002", "order_key": "a5"},
        ]
        result = reorder_ws_index({}, new_order)
        ws_ids = [e["ws_id"] for e in result["ws_index"]]
        assert ws_ids == ["WS-WB-001", "WS-WB-002", "WS-WB-003"]

    def test_reorder_replaces_entirely(self):
        wp = {
            "ws_index": [
                {"ws_id": "WS-WB-001", "order_key": "a0"},
                {"ws_id": "WS-WB-002", "order_key": "a1"},
                {"ws_id": "WS-WB-003", "order_key": "a2"},
            ]
        }
        new_order = [
            {"ws_id": "WS-WB-001", "order_key": "a0"},
        ]
        result = reorder_ws_index(wp, new_order)
        assert len(result["ws_index"]) == 1

    def test_reorder_empty_list(self):
        wp = {
            "ws_index": [
                {"ws_id": "WS-WB-001", "order_key": "a0"},
            ]
        }
        result = reorder_ws_index(wp, [])
        assert result["ws_index"] == []

    def test_reorder_only_copies_ws_id_and_order_key(self):
        """Extra fields in new_order entries should be stripped."""
        new_order = [
            {"ws_id": "WS-WB-001", "order_key": "a0", "extra": "junk"},
        ]
        result = reorder_ws_index({}, new_order)
        entry = result["ws_index"][0]
        assert "extra" not in entry
        assert set(entry.keys()) == {"ws_id", "order_key"}
