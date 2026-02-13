"""Tests for remediation loop."""

import pytest

from app.domain.workflow.remediation import RemediationLoop, RemediationContext
from app.domain.workflow.step_state import QAFinding, QAResult, StepState


class TestRemediationLoop:
    """Tests for RemediationLoop."""
    
    @pytest.fixture
    def loop(self):
        return RemediationLoop(max_attempts=3)
    
    def test_should_retry_when_failed_and_attempts_remain(self, loop):
        state = StepState(step_id="test", max_attempts=3)
        state.start()
        qa_result = QAResult(
            passed=False,
            findings=[QAFinding(path="$", message="error", severity="error")]
        )
        assert loop.should_retry(state, qa_result) is True
    
    def test_should_not_retry_when_passed(self, loop):
        state = StepState(step_id="test", max_attempts=3)
        state.start()
        qa_result = QAResult(passed=True)
        assert loop.should_retry(state, qa_result) is False
    
    def test_should_not_retry_when_exhausted(self, loop):
        state = StepState(step_id="test", max_attempts=3)
        state.attempt = 3
        qa_result = QAResult(
            passed=False,
            findings=[QAFinding(path="$", message="error", severity="error")]
        )
        assert loop.should_retry(state, qa_result) is False
    
    def test_should_not_retry_warnings_only(self, loop):
        state = StepState(step_id="test", max_attempts=3)
        state.start()
        qa_result = QAResult(
            passed=False,
            findings=[QAFinding(path="$", message="warning", severity="warning")]
        )
        assert loop.should_retry(state, qa_result) is False
    
    def test_build_remediation_prompt_includes_original(self, loop):
        context = RemediationContext(
            original_prompt="Do the thing",
            findings=[QAFinding(path="$.field", message="Missing field", severity="error")],
            attempt=1,
            max_attempts=3,
        )
        prompt = loop.build_remediation_prompt(context)
        assert "Do the thing" in prompt
        assert "Original Task" in prompt
    
    def test_build_remediation_prompt_includes_findings(self, loop):
        context = RemediationContext(
            original_prompt="Do the thing",
            findings=[
                QAFinding(path="$.name", message="Name required", severity="error", rule="required"),
                QAFinding(path="$.count", message="Should be positive", severity="warning"),
            ],
            attempt=1,
            max_attempts=3,
        )
        prompt = loop.build_remediation_prompt(context)
        assert "Name required" in prompt
        assert "$.name" in prompt
        assert "ERROR" in prompt
    
    def test_build_remediation_prompt_includes_attempt_info(self, loop):
        context = RemediationContext(
            original_prompt="Do the thing",
            findings=[QAFinding(path="$", message="error", severity="error")],
            attempt=2,
            max_attempts=3,
        )
        prompt = loop.build_remediation_prompt(context)
        assert "attempt 3 of 3" in prompt
    
    def test_build_context_from_state(self, loop):
        state = StepState(step_id="test", max_attempts=3)
        state.start()
        state.raw_llm_response = '{"bad": "output"}'
        qa_result = QAResult(
            passed=False,
            findings=[QAFinding(path="$", message="error", severity="error")]
        )
        context = loop.build_context("Original prompt", state, qa_result)
        assert context.original_prompt == "Original prompt"
        assert context.attempt == 1
        assert context.previous_output == '{"bad": "output"}'
    
    def test_get_error_summary(self, loop):
        findings = [
            QAFinding(path="a", message="", severity="error"),
            QAFinding(path="b", message="", severity="error"),
            QAFinding(path="c", message="", severity="warning"),
        ]
        summary = loop.get_error_summary(findings)
        assert "2 error(s)" in summary
        assert "1 warning(s)" in summary
    
    def test_get_error_summary_empty(self, loop):
        summary = loop.get_error_summary([])
        assert summary == "no issues"
