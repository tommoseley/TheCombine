"""
Tests for validator pure functions -- WS-CRAP-004.

Tests extracted pure functions: is_pow_ref_resolvable, validate_field.
"""

from app.api.services.mech_handlers.validator import (
    is_pow_ref_resolvable,
    validate_field,
    KNOWN_POW_REFS,
)


# =========================================================================
# is_pow_ref_resolvable
# =========================================================================


class TestIsPowRefResolvable:
    """Tests for is_pow_ref_resolvable pure function."""

    def test_known_ref_resolves(self):
        assert is_pow_ref_resolvable("pow:software_product_development@1.0.0")

    def test_all_known_refs_resolve(self):
        for ref in KNOWN_POW_REFS:
            assert is_pow_ref_resolvable(ref), f"{ref} should resolve"

    def test_unknown_ref_fails_with_must_resolve(self):
        assert not is_pow_ref_resolvable("pow:unknown@1.0.0", must_resolve=True)

    def test_unknown_ref_passes_without_must_resolve(self):
        assert is_pow_ref_resolvable("pow:unknown@1.0.0", must_resolve=False)

    def test_non_pow_prefix_fails_without_must_resolve(self):
        assert not is_pow_ref_resolvable("not_a_pow_ref", must_resolve=False)

    def test_empty_string_fails(self):
        assert not is_pow_ref_resolvable("")

    def test_none_fails(self):
        assert not is_pow_ref_resolvable(None)

    def test_custom_known_refs(self):
        custom = {"pow:custom@1.0.0"}
        assert is_pow_ref_resolvable("pow:custom@1.0.0", known_refs=custom)
        assert not is_pow_ref_resolvable(
            "pow:software_product_development@1.0.0", known_refs=custom
        )

    def test_empty_known_refs_with_must_resolve(self):
        assert not is_pow_ref_resolvable(
            "pow:anything@1.0.0", must_resolve=True, known_refs=set()
        )


# =========================================================================
# validate_field
# =========================================================================


class TestValidateField:
    """Tests for validate_field pure function."""

    def test_required_check_passes(self):
        data = {"name": "test"}
        config = {"path": "$.name", "check": "required", "error_code": "missing"}
        assert validate_field(data, config) is None

    def test_required_check_fails(self):
        data = {}
        config = {
            "path": "$.name",
            "check": "required",
            "error_code": "missing_name",
            "error_message": "Name is required",
        }
        error = validate_field(data, config)
        assert error is not None
        assert error["code"] == "missing_name"
        assert error["message"] == "Name is required"

    def test_enum_check_passes(self):
        data = {"status": "active"}
        config = {
            "path": "$.status",
            "check": "enum",
            "allowed": ["active", "inactive"],
            "error_code": "invalid_status",
        }
        assert validate_field(data, config) is None

    def test_enum_check_fails(self):
        data = {"status": "unknown"}
        config = {
            "path": "$.status",
            "check": "enum",
            "allowed": ["active", "inactive"],
            "error_code": "invalid_status",
            "error_message": "Status must be active or inactive",
        }
        error = validate_field(data, config)
        assert error is not None
        assert error["code"] == "invalid_status"

    def test_equals_check_passes(self):
        data = {"version": "1.0.0"}
        config = {
            "path": "$.version",
            "check": "equals",
            "expected": "1.0.0",
            "error_code": "wrong_version",
        }
        assert validate_field(data, config) is None

    def test_equals_check_fails(self):
        data = {"version": "2.0.0"}
        config = {
            "path": "$.version",
            "check": "equals",
            "expected": "1.0.0",
            "error_code": "wrong_version",
            "error_message": "Must be version 1.0.0",
        }
        error = validate_field(data, config)
        assert error is not None
        assert error["code"] == "wrong_version"

    def test_pow_ref_resolvable_check_passes(self):
        data = {"decision": {"next_pow_ref": "pow:software_product_development@1.0.0"}}
        config = {
            "path": "$.decision.next_pow_ref",
            "check": "pow_ref_resolvable",
            "error_code": "unresolvable",
        }
        assert validate_field(data, config) is None

    def test_pow_ref_resolvable_check_fails(self):
        data = {"decision": {"next_pow_ref": "pow:nonexistent@1.0.0"}}
        config = {
            "path": "$.decision.next_pow_ref",
            "check": "pow_ref_resolvable",
            "error_code": "unresolvable",
            "error_message": "POW ref not found",
        }
        error = validate_field(data, config)
        assert error is not None
        assert error["code"] == "unresolvable"

    def test_pow_ref_resolvable_with_must_resolve_false(self):
        data = {"decision": {"next_pow_ref": "pow:unknown@1.0.0"}}
        config = {
            "path": "$.decision.next_pow_ref",
            "check": "pow_ref_resolvable",
            "error_code": "unresolvable",
        }
        global_config = {"must_resolve_pow_ref": False}
        assert validate_field(data, config, global_config) is None

    def test_invalid_jsonpath(self):
        data = {"name": "test"}
        config = {
            "path": "$[invalid",
            "check": "required",
            "error_code": "missing",
        }
        error = validate_field(data, config)
        assert error is not None
        assert error["code"] == "invalid_path"

    def test_default_error_code_and_message(self):
        data = {}
        config = {"path": "$.missing", "check": "required"}
        error = validate_field(data, config)
        assert error["code"] == "validation_failed"
        assert error["message"] == "Validation failed"

    def test_nested_jsonpath(self):
        data = {"a": {"b": {"c": "value"}}}
        config = {"path": "$.a.b.c", "check": "equals", "expected": "value"}
        assert validate_field(data, config) is None
