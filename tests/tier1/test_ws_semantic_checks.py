"""Tier-1 tests for WS evaluator semantic presence checks.

Pure unit tests — no DB, no LLM calls.
"""

from app.domain.services.ws_defect_evaluator import evaluate_ws


def _good_ws():
    return {
        "ws_id": "WS-001",
        "objective": "Implement user authentication with bcrypt password hashing and JWT sessions",
        "scope_in": ["Login endpoint with input validation", "Password hashing with bcrypt"],
        "scope_out": ["OAuth integration deferred"],
        "procedure": [
            "Write failing tests for login endpoint with valid and invalid credentials",
            "Implement login route handler with bcrypt password verification",
            "Add JWT session token generation and validation middleware",
            "Verify all tests pass and no regressions in existing test suite",
        ],
        "verification_criteria": [
            "Login endpoint returns 200 with valid credentials and JWT token",
            "Login endpoint returns 401 with invalid credentials",
            "JWT middleware rejects expired or malformed tokens",
        ],
        "allowed_paths": ["app/auth/", "tests/tier1/auth/"],
        "prohibited_actions": ["Do not modify existing user model"],
        "governance_pins": {
            "ta_version_id": "TA-v1.0",
            "policy_refs": ["POL-WS-001"],
            "adr_refs": [],
        },
    }


class TestWSSemanticChecks:

    def test_good_ws_no_semantic_failures(self):
        report = evaluate_ws(_good_ws())
        sem = [c for c in report.checks if c["check_id"].startswith("semantic_")]
        failures = [c for c in sem if c["status"] == "fail"]
        assert len(failures) == 0

    def test_weak_objective_flagged(self):
        ws = _good_ws()
        ws["objective"] = "Do stuff"
        report = evaluate_ws(ws)
        sem = [c for c in report.checks if c["check_id"] == "semantic_objective"]
        assert sem[0]["status"] == "fail"
        assert "WEAK" in sem[0]["evidence"]

    def test_empty_objective_flagged(self):
        ws = _good_ws()
        ws["objective"] = ""
        report = evaluate_ws(ws)
        sem = [c for c in report.checks if c["check_id"] == "semantic_objective"]
        assert sem[0]["status"] == "fail"
        assert "EMPTY" in sem[0]["evidence"]

    def test_absent_objective_flagged(self):
        ws = _good_ws()
        del ws["objective"]
        report = evaluate_ws(ws)
        sem = [c for c in report.checks if c["check_id"] == "semantic_objective"]
        assert sem[0]["status"] == "fail"
        assert "ABSENT" in sem[0]["evidence"]

    def test_weak_scope_flagged(self):
        ws = _good_ws()
        ws["scope_in"] = ["stuff"]
        ws["scope_out"] = []
        report = evaluate_ws(ws)
        sem = [c for c in report.checks if c["check_id"] == "semantic_scope"]
        assert sem[0]["status"] == "fail"

    def test_weak_procedure_flagged(self):
        ws = _good_ws()
        ws["procedure"] = ["TBD"]
        report = evaluate_ws(ws)
        sem = [c for c in report.checks if c["check_id"] == "semantic_procedure"]
        assert sem[0]["status"] == "fail"

    def test_weak_verification_flagged(self):
        ws = _good_ws()
        ws["verification_criteria"] = ["N/A"]
        report = evaluate_ws(ws)
        sem = [c for c in report.checks if c["check_id"] == "semantic_verification_criteria"]
        assert sem[0]["status"] == "fail"

    def test_good_procedure_passes(self):
        report = evaluate_ws(_good_ws())
        sem = [c for c in report.checks if c["check_id"] == "semantic_procedure"]
        assert sem[0]["status"] == "pass"

    def test_evaluator_version_bumped(self):
        report = evaluate_ws(_good_ws())
        assert report.evaluator_version == "1.1"

    def test_total_check_count(self):
        report = evaluate_ws(_good_ws())
        # 5 structural + 4 semantic = 9
        assert len(report.checks) == 9
