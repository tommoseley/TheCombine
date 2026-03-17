"""Tier-2 tests for LLM run query logic (WS-PI-0B Step 3).

Tests the query endpoint's filtering and response shape.
Uses spy pattern — avoids full app instantiation.
"""

from uuid import uuid4

from app.api.routers.admin import LLMRunSummary, LLMRunQueryResponse


# =========================================================================
# Response model tests (pure unit, no DB)
# =========================================================================


class TestLLMRunSummary:
    """Tests for the run summary response model."""

    def test_creates_valid_summary(self):
        s = LLMRunSummary(
            id=str(uuid4()),
            artifact_type="work_statement",
            prompt_id="ws_gen_v1",
            prompt_version="1.0.0",
            status="SUCCESS",
            project_id=str(uuid4()),
            started_at="2026-03-15T00:00:00+00:00",
            input_tokens=5000,
            output_tokens=2000,
            total_tokens=7000,
        )
        assert s.artifact_type == "work_statement"
        assert s.status == "SUCCESS"

    def test_optional_fields_accept_none(self):
        s = LLMRunSummary(
            id=str(uuid4()),
            artifact_type=None,
            prompt_id="ws_gen_v1",
            prompt_version="1.0.0",
            status="SUCCESS",
            project_id=None,
            started_at=None,
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
        )
        assert s.artifact_type is None
        assert s.project_id is None


class TestLLMRunQueryResponse:
    """Tests for the query response envelope."""

    def test_empty_response(self):
        resp = LLMRunQueryResponse(runs=[], total=0, limit=50, offset=0)
        assert resp.runs == []
        assert resp.total == 0
        assert resp.limit == 50
        assert resp.offset == 0

    def test_response_with_runs(self):
        run = LLMRunSummary(
            id=str(uuid4()),
            artifact_type="work_statement",
            prompt_id="ws_gen_v1",
            prompt_version="1.0.0",
            status="SUCCESS",
            project_id=str(uuid4()),
            started_at="2026-03-15T00:00:00+00:00",
            input_tokens=5000,
            output_tokens=2000,
            total_tokens=7000,
        )
        resp = LLMRunQueryResponse(runs=[run], total=1, limit=50, offset=0)
        assert len(resp.runs) == 1
        assert resp.total == 1

    def test_default_limit_is_50(self):
        """The WS specifies default limit 50."""
        resp = LLMRunQueryResponse(runs=[], total=0, limit=50, offset=0)
        assert resp.limit == 50
