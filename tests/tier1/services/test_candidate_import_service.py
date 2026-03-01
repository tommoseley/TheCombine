"""Tests for Candidate Import Service (WS-WB-003).

Tier-1 tests for candidate_import_service:
- extract_candidates_from_ip: extraction from v3/v2/v1 field names
- build_wpc_document: field mapping from IP candidate to WPC schema
- import_candidates: full pipeline (extract + transform)

Pure business logic -- no DB, no handlers, no external dependencies.
"""

import copy
from datetime import datetime


from app.domain.services.candidate_import_service import (
    extract_candidates_from_ip,
    build_wpc_document,
    import_candidates,
)


# ---------------------------------------------------------------------------
# Fixtures -- baseline IP content with candidates
# ---------------------------------------------------------------------------

def _ip_content_v3() -> dict:
    """IP content using v3 field name: work_package_candidates."""
    return {
        "title": "Test Implementation Plan",
        "work_package_candidates": [
            {
                "candidate_id": "WPC-001",
                "title": "Registry Service",
                "rationale": "Centralize handler registration",
                "scope_in": ["handler registry", "config loading"],
                "scope_out": ["UI components"],
                "dependencies": [],
                "definition_of_done": ["All handlers registered"],
            },
            {
                "candidate_id": "WPC-002",
                "title": "Schema Validation",
                "rationale": "Enforce output schemas",
                "scope_in": ["schema validation"],
                "scope_out": [],
                "dependencies": ["WPC-001"],
                "definition_of_done": ["Schemas enforced"],
            },
        ],
    }


def _ip_content_v2() -> dict:
    """IP content using v2 field name: candidate_work_packages."""
    return {
        "title": "Legacy V2 IP",
        "candidate_work_packages": [
            {
                "candidate_id": "WPC-001",
                "title": "Single Candidate",
                "rationale": "Only one",
                "scope_in": ["everything"],
                "scope_out": [],
                "dependencies": [],
                "definition_of_done": ["Done"],
            },
        ],
    }


def _ip_content_v1() -> dict:
    """IP content using v1 field name: work_packages."""
    return {
        "title": "Legacy V1 IP",
        "work_packages": [
            {
                "candidate_id": "WPC-001",
                "title": "Old Candidate",
                "rationale": "From v1",
                "scope_in": ["old scope"],
                "scope_out": [],
                "dependencies": [],
                "definition_of_done": ["Pass"],
            },
        ],
    }


def _single_candidate() -> dict:
    """A single IP candidate entry."""
    return {
        "candidate_id": "WPC-001",
        "title": "Registry Service",
        "rationale": "Centralize handler registration",
        "scope_in": ["handler registry", "config loading"],
        "scope_out": ["UI components"],
        "dependencies": [],
        "definition_of_done": ["All handlers registered"],
    }


# ===========================================================================
# extract_candidates_from_ip tests
# ===========================================================================

class TestExtractCandidatesFromIP:
    """Tests for extract_candidates_from_ip()."""

    def test_extracts_from_v3_field(self):
        """Extracts candidates from work_package_candidates (v3)."""
        ip = _ip_content_v3()
        result = extract_candidates_from_ip(ip)
        assert len(result) == 2
        assert result[0]["candidate_id"] == "WPC-001"
        assert result[1]["candidate_id"] == "WPC-002"

    def test_extracts_from_v2_field(self):
        """Extracts candidates from candidate_work_packages (v2)."""
        ip = _ip_content_v2()
        result = extract_candidates_from_ip(ip)
        assert len(result) == 1
        assert result[0]["candidate_id"] == "WPC-001"

    def test_extracts_from_v1_field(self):
        """Extracts candidates from work_packages (v1)."""
        ip = _ip_content_v1()
        result = extract_candidates_from_ip(ip)
        assert len(result) == 1
        assert result[0]["candidate_id"] == "WPC-001"

    def test_v3_takes_priority_over_v2(self):
        """When both v3 and v2 fields exist, v3 is used."""
        ip = _ip_content_v3()
        ip["candidate_work_packages"] = [
            {
                "candidate_id": "WPC-099",
                "title": "Should Not Appear",
                "rationale": "v2 ignored",
                "scope_in": [],
                "scope_out": [],
                "dependencies": [],
                "definition_of_done": [],
            },
        ]
        result = extract_candidates_from_ip(ip)
        assert len(result) == 2
        assert result[0]["candidate_id"] == "WPC-001"

    def test_v2_takes_priority_over_v1(self):
        """When both v2 and v1 fields exist, v2 is used."""
        ip = _ip_content_v2()
        ip["work_packages"] = [
            {
                "candidate_id": "WPC-099",
                "title": "Should Not Appear",
                "rationale": "v1 ignored",
                "scope_in": [],
                "scope_out": [],
                "dependencies": [],
                "definition_of_done": [],
            },
        ]
        result = extract_candidates_from_ip(ip)
        assert len(result) == 1
        assert result[0]["candidate_id"] == "WPC-001"

    def test_returns_empty_when_no_candidates_field(self):
        """Returns empty list when IP has no candidate field."""
        ip = {"title": "No Candidates IP"}
        result = extract_candidates_from_ip(ip)
        assert result == []

    def test_returns_empty_when_candidates_field_is_empty(self):
        """Returns empty list when candidates field is an empty list."""
        ip = {"work_package_candidates": []}
        result = extract_candidates_from_ip(ip)
        assert result == []

    def test_does_not_mutate_ip_content(self):
        """extract_candidates_from_ip does not mutate the input dict."""
        ip = _ip_content_v3()
        original = copy.deepcopy(ip)
        extract_candidates_from_ip(ip)
        assert ip == original


# ===========================================================================
# build_wpc_document tests
# ===========================================================================

class TestBuildWPCDocument:
    """Tests for build_wpc_document()."""

    def test_maps_candidate_id_to_wpc_id(self):
        """candidate_id from IP maps to wpc_id in WPC document."""
        candidate = _single_candidate()
        result = build_wpc_document(candidate, "ip-doc-123", "1", "system")
        assert result["wpc_id"] == "WPC-001"

    def test_maps_title(self):
        """title is preserved from candidate."""
        candidate = _single_candidate()
        result = build_wpc_document(candidate, "ip-doc-123", "1", "system")
        assert result["title"] == "Registry Service"

    def test_maps_rationale(self):
        """rationale is preserved from candidate."""
        candidate = _single_candidate()
        result = build_wpc_document(candidate, "ip-doc-123", "1", "system")
        assert result["rationale"] == "Centralize handler registration"

    def test_maps_scope_in_to_scope_summary(self):
        """scope_in from IP maps to scope_summary in WPC document."""
        candidate = _single_candidate()
        result = build_wpc_document(candidate, "ip-doc-123", "1", "system")
        assert result["scope_summary"] == ["handler registry", "config loading"]

    def test_sets_source_ip_id(self):
        """source_ip_id is set from the provided IP document ID."""
        candidate = _single_candidate()
        result = build_wpc_document(candidate, "ip-doc-abc", "1", "system")
        assert result["source_ip_id"] == "ip-doc-abc"

    def test_sets_source_ip_version(self):
        """source_ip_version is set from the provided version."""
        candidate = _single_candidate()
        result = build_wpc_document(candidate, "ip-doc-abc", "3", "system")
        assert result["source_ip_version"] == "3"

    def test_sets_frozen_by(self):
        """frozen_by is set from the provided actor."""
        candidate = _single_candidate()
        result = build_wpc_document(candidate, "ip-doc-abc", "1", "tom")
        assert result["frozen_by"] == "tom"

    def test_sets_frozen_at_as_iso_datetime(self):
        """frozen_at is set to an ISO datetime string."""
        candidate = _single_candidate()
        result = build_wpc_document(candidate, "ip-doc-abc", "1", "system")
        assert "frozen_at" in result
        # Should be parseable as ISO datetime
        dt = datetime.fromisoformat(result["frozen_at"])
        assert dt.tzinfo is not None  # Must be timezone-aware

    def test_output_has_all_required_wpc_fields(self):
        """Output contains all fields required by the WPC schema."""
        candidate = _single_candidate()
        result = build_wpc_document(candidate, "ip-doc-abc", "1", "system")
        required_fields = [
            "wpc_id", "title", "rationale", "scope_summary",
            "source_ip_id", "source_ip_version", "frozen_at", "frozen_by",
        ]
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

    def test_output_has_no_extra_fields(self):
        """Output contains only the fields defined in the WPC schema."""
        candidate = _single_candidate()
        result = build_wpc_document(candidate, "ip-doc-abc", "1", "system")
        allowed_fields = {
            "wpc_id", "title", "rationale", "scope_summary",
            "source_ip_id", "source_ip_version", "frozen_at", "frozen_by",
        }
        assert set(result.keys()) == allowed_fields

    def test_empty_scope_in_produces_empty_scope_summary(self):
        """Empty scope_in in candidate maps to empty scope_summary."""
        candidate = _single_candidate()
        candidate["scope_in"] = []
        result = build_wpc_document(candidate, "ip-doc-abc", "1", "system")
        assert result["scope_summary"] == []

    def test_missing_scope_in_produces_empty_scope_summary(self):
        """Missing scope_in in candidate maps to empty scope_summary."""
        candidate = _single_candidate()
        del candidate["scope_in"]
        result = build_wpc_document(candidate, "ip-doc-abc", "1", "system")
        assert result["scope_summary"] == []


# ===========================================================================
# import_candidates tests
# ===========================================================================

class TestImportCandidates:
    """Tests for import_candidates()."""

    def test_returns_list_of_wpc_documents(self):
        """import_candidates returns a list of WPC document dicts."""
        ip = _ip_content_v3()
        result = import_candidates(ip, "ip-doc-123", "1")
        assert isinstance(result, list)
        assert len(result) == 2

    def test_each_result_is_valid_wpc(self):
        """Each returned WPC has all required fields."""
        ip = _ip_content_v3()
        result = import_candidates(ip, "ip-doc-123", "1")
        required_fields = [
            "wpc_id", "title", "rationale", "scope_summary",
            "source_ip_id", "source_ip_version", "frozen_at", "frozen_by",
        ]
        for wpc in result:
            for field in required_fields:
                assert field in wpc, f"Missing field {field} in WPC {wpc.get('wpc_id')}"

    def test_preserves_candidate_order(self):
        """Candidates are returned in the same order as in the IP."""
        ip = _ip_content_v3()
        result = import_candidates(ip, "ip-doc-123", "1")
        assert result[0]["wpc_id"] == "WPC-001"
        assert result[1]["wpc_id"] == "WPC-002"

    def test_default_frozen_by_is_system(self):
        """Default frozen_by is 'system'."""
        ip = _ip_content_v3()
        result = import_candidates(ip, "ip-doc-123", "1")
        for wpc in result:
            assert wpc["frozen_by"] == "system"

    def test_custom_frozen_by(self):
        """Custom frozen_by is passed through to all candidates."""
        ip = _ip_content_v3()
        result = import_candidates(ip, "ip-doc-123", "1", frozen_by="tom")
        for wpc in result:
            assert wpc["frozen_by"] == "tom"

    def test_empty_ip_returns_empty_list(self):
        """IP with no candidates returns empty list."""
        ip = {"title": "Empty IP"}
        result = import_candidates(ip, "ip-doc-123", "1")
        assert result == []

    def test_source_ip_id_set_on_all_candidates(self):
        """source_ip_id is consistent across all returned WPCs."""
        ip = _ip_content_v3()
        result = import_candidates(ip, "ip-doc-xyz", "2")
        for wpc in result:
            assert wpc["source_ip_id"] == "ip-doc-xyz"
            assert wpc["source_ip_version"] == "2"

    def test_does_not_mutate_ip_content(self):
        """import_candidates does not mutate the input IP content."""
        ip = _ip_content_v3()
        original = copy.deepcopy(ip)
        import_candidates(ip, "ip-doc-123", "1")
        assert ip == original
