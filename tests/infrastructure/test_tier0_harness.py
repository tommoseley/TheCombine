"""Tier 0 harness verification tests (WS-ADR-050-001).

These tests verify that ops/scripts/tier0.sh correctly detects failures
and returns appropriate exit codes. Each test corresponds to a Tier 1
verification criterion from WS-ADR-050-001.

Hardening additions (ADR-050 Mode B enforcement):
- Missing tooling is a FAIL unless --allow-missing declares Mode B
- --allow-missing rejected in CI unless ALLOW_MODE_B_IN_CI=1
- Frontend build auto-detects spa/ changes (tracked + untracked)
- Machine-readable JSON with schema_version, timing, exit_code

Test approach: subprocess invocation of the harness script with
deliberately introduced violations, verifying exit codes.
"""

import json
import os
import subprocess
import textwrap

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HARNESS = os.path.join(REPO_ROOT, "ops", "scripts", "tier0.sh")

# All tests that aren't specifically testing typecheck behavior need this
# flag because mypy is not installed (Mode B debt).
ALLOW_MISSING_TYPECHECK = ["--allow-missing", "typecheck"]


def run_harness(*args, timeout=300, env_override=None):
    """Run the Tier 0 harness and return the CompletedProcess."""
    env = os.environ.copy()
    # Ensure CI is not set for normal tests (avoid CI guard interference)
    env.pop("CI", None)
    env.pop("ALLOW_MODE_B_IN_CI", None)
    if env_override:
        env.update(env_override)
    return subprocess.run(
        [HARNESS, *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )


def extract_json(stdout):
    """Extract the machine-readable JSON block from harness output."""
    for line in stdout.splitlines():
        if line.startswith("{") and '"schema_version"' in line:
            return json.loads(line)
    return None


# ---------------------------------------------------------------------------
# Criterion 1: Tier 0 returns non-zero when pytest fails
# ---------------------------------------------------------------------------
class TestCriterion1PytestFailure:
    """Introduce a deliberately failing test, run harness, assert exit != 0."""

    FAILING_TEST = os.path.join(
        REPO_ROOT, "tests", "_tier0_deliberate_fail_test.py"
    )

    def setup_method(self):
        with open(self.FAILING_TEST, "w") as f:
            f.write(
                textwrap.dedent("""\
                    def test_deliberate_failure():
                        assert False, "Deliberate failure for Tier 0 harness test"
                """)
            )

    def teardown_method(self):
        if os.path.exists(self.FAILING_TEST):
            os.remove(self.FAILING_TEST)

    def test_harness_fails_on_pytest_failure(self):
        result = run_harness(*ALLOW_MISSING_TYPECHECK)
        assert result.returncode != 0, (
            "Tier 0 harness must return non-zero when pytest has failures"
        )


# ---------------------------------------------------------------------------
# Criterion 2: Tier 0 returns non-zero when lint fails
# ---------------------------------------------------------------------------
class TestCriterion2LintFailure:
    """Introduce a deliberate lint violation, run harness, assert exit != 0."""

    LINT_VIOLATION = os.path.join(
        REPO_ROOT, "app", "_tier0_lint_violation.py"
    )

    def setup_method(self):
        with open(self.LINT_VIOLATION, "w") as f:
            f.write(
                textwrap.dedent("""\
                    import os
                    import sys
                    # Unused imports — ruff F401
                """)
            )

    def teardown_method(self):
        if os.path.exists(self.LINT_VIOLATION):
            os.remove(self.LINT_VIOLATION)

    def test_harness_fails_on_lint_violation(self):
        result = run_harness(*ALLOW_MISSING_TYPECHECK)
        assert result.returncode != 0, (
            "Tier 0 harness must return non-zero when lint violations exist"
        )


# ---------------------------------------------------------------------------
# Criterion 3: Missing type checker fails without Mode B declaration
# ---------------------------------------------------------------------------
class TestCriterion3TypeCheckMissing:
    """Without --allow-missing, a missing type checker must cause failure.

    This is the Mode A enforcement: missing tooling is not silently skipped.
    """

    def test_harness_fails_when_typecheck_missing(self):
        # Run WITHOUT --allow-missing typecheck
        result = run_harness()
        data = extract_json(result.stdout)

        if data and data["checks"]["typecheck"] == "PASS":
            pytest.skip("mypy is installed — cannot test missing-tool failure")

        assert result.returncode != 0, (
            "Tier 0 must return non-zero when mypy is missing and "
            "no --allow-missing typecheck is declared"
        )
        assert data is not None, "Machine-readable JSON must be emitted"
        assert data["checks"]["typecheck"] == "FAIL", (
            "typecheck must be FAIL (not SKIP) when mypy is missing without Mode B"
        )


# ---------------------------------------------------------------------------
# Criterion 3b: Mode B allows missing type checker with explicit declaration
# ---------------------------------------------------------------------------
class TestCriterion3bModeBTypeCheck:
    """With --allow-missing typecheck, missing mypy is SKIP_B, not failure."""

    def test_mode_b_allows_missing_typecheck(self):
        result = run_harness(*ALLOW_MISSING_TYPECHECK)
        data = extract_json(result.stdout)

        if data and data["checks"]["typecheck"] == "PASS":
            pytest.skip("mypy is installed — Mode B not triggered")

        assert "B-MODE ACTIVE" in result.stdout, (
            "Harness must print B-MODE ACTIVE when Mode B exception is used"
        )
        assert data is not None, "Machine-readable JSON must be emitted"
        assert data["checks"]["typecheck"] == "SKIP_B", (
            "typecheck must be SKIP_B (not SKIP or FAIL) under Mode B"
        )
        assert "typecheck" in data["mode_b"], (
            "typecheck must appear in mode_b array"
        )


# ---------------------------------------------------------------------------
# Criterion 4: Tier 0 returns non-zero when frontend build fails
# ---------------------------------------------------------------------------
class TestCriterion4FrontendBuildFailure:
    """Corrupt SPA entry point — harness auto-detects spa/ change and fails."""

    ENTRY_POINT = os.path.join(REPO_ROOT, "spa", "src", "main.jsx")

    def setup_method(self):
        if not os.path.isfile(self.ENTRY_POINT):
            pytest.skip("spa/src/main.jsx does not exist — no frontend to test")
        with open(self.ENTRY_POINT, "r") as f:
            self._original_content = f.read()
        with open(self.ENTRY_POINT, "a") as f:
            f.write("\n// TIER0 TEST — DELIBERATE SYNTAX ERROR\nexport const {{{ = broken;\n")

    def teardown_method(self):
        if hasattr(self, "_original_content"):
            with open(self.ENTRY_POINT, "w") as f:
                f.write(self._original_content)

    def test_harness_fails_on_frontend_build_error(self):
        # No --frontend flag: auto-detection of spa/ changes should trigger build
        result = run_harness(*ALLOW_MISSING_TYPECHECK)
        assert result.returncode != 0, (
            "Tier 0 harness must return non-zero when frontend build fails"
        )
        assert "auto-detected spa/ changes" in result.stdout, (
            "Harness must auto-detect spa/ changes without --frontend flag"
        )


# ---------------------------------------------------------------------------
# Criterion 5: Tier 0 returns non-zero when scope validation fails
# ---------------------------------------------------------------------------
class TestCriterion5ScopeViolation:
    """Modify a file outside declared scope, run harness with --scope, assert exit != 0."""

    OUT_OF_SCOPE_FILE = os.path.join(
        REPO_ROOT, "docs", "_tier0_scope_violation.txt"
    )

    def setup_method(self):
        with open(self.OUT_OF_SCOPE_FILE, "w") as f:
            f.write("Deliberate out-of-scope modification\n")
        # Stage the file so git diff --cached detects it
        subprocess.run(
            ["git", "add", self.OUT_OF_SCOPE_FILE],
            cwd=REPO_ROOT,
            capture_output=True,
        )

    def teardown_method(self):
        subprocess.run(
            ["git", "reset", "HEAD", self.OUT_OF_SCOPE_FILE],
            cwd=REPO_ROOT,
            capture_output=True,
        )
        if os.path.exists(self.OUT_OF_SCOPE_FILE):
            os.remove(self.OUT_OF_SCOPE_FILE)

    def test_harness_fails_on_scope_violation(self):
        # Declare scope as only app/ — the docs/ file is out of scope
        result = run_harness("--scope", "app/", *ALLOW_MISSING_TYPECHECK)
        assert result.returncode != 0, (
            "Tier 0 harness must return non-zero when files outside "
            "declared scope are modified"
        )


# ---------------------------------------------------------------------------
# Criterion 6: Tier 0 returns zero on a clean repository
# ---------------------------------------------------------------------------
class TestCriterion6CleanPass:
    """Run harness with no violations present, assert exit code == 0."""

    def test_harness_passes_on_clean_repo(self):
        # Must declare Mode B for missing mypy — this is honest, not a loophole
        result = run_harness(*ALLOW_MISSING_TYPECHECK)
        assert result.returncode == 0, (
            f"Tier 0 harness must return zero on clean repo.\n"
            f"stdout: {result.stdout[-500:]}\n"
            f"stderr: {result.stderr[-500:]}"
        )


# ---------------------------------------------------------------------------
# Machine-readable output: schema contract
# ---------------------------------------------------------------------------
class TestMachineReadableOutput:
    """Verify the harness emits parseable JSON with required fields."""

    def test_json_schema_version_and_fields(self):
        result = run_harness(*ALLOW_MISSING_TYPECHECK)
        assert "--- TIER0_JSON ---" in result.stdout, (
            "Harness must emit --- TIER0_JSON --- marker"
        )
        data = extract_json(result.stdout)
        assert data is not None, "JSON block must be parseable"

        # schema_version for forward compatibility
        assert data["schema_version"] == 1, (
            "schema_version must be 1"
        )

        # Core fields
        assert data["overall"] in ("PASS", "FAIL")
        assert isinstance(data["exit_code"], int)
        assert isinstance(data["mode_b"], list)
        assert isinstance(data["changed_files"], list)

        # Timing
        assert "started_at" in data, "Must include started_at timestamp"
        assert "T" in data["started_at"], "started_at must be ISO 8601"
        assert "duration_ms" in data, "Must include duration_ms"
        assert isinstance(data["duration_ms"], int)
        assert data["duration_ms"] >= 0

        # All five checks present
        for check in ("pytest", "lint", "typecheck", "frontend", "scope"):
            assert check in data["checks"], f"Missing check: {check}"

    def test_json_emitted_on_failure(self):
        """JSON must be emitted even when harness fails (for downstream parsing)."""
        # Run without --allow-missing; mypy missing will cause failure
        result = run_harness()
        data = extract_json(result.stdout)
        assert data is not None, (
            "JSON must be emitted even on FAIL — downstream tools need it"
        )
        assert data["overall"] == "FAIL"
        assert data["exit_code"] != 0


# ---------------------------------------------------------------------------
# CI guard: --allow-missing rejected under CI=true
# ---------------------------------------------------------------------------
class TestCIGuard:
    """In CI, --allow-missing must be rejected unless ALLOW_MODE_B_IN_CI=1."""

    def test_ci_rejects_allow_missing(self):
        result = run_harness(
            *ALLOW_MISSING_TYPECHECK,
            env_override={"CI": "true"},
        )
        assert result.returncode != 0, (
            "CI=true must reject --allow-missing without ALLOW_MODE_B_IN_CI=1"
        )
        assert "not permitted in CI" in result.stderr, (
            "Must print CI rejection message to stderr"
        )

    def test_ci_allows_mode_b_with_explicit_override(self):
        result = run_harness(
            *ALLOW_MISSING_TYPECHECK,
            env_override={"CI": "true", "ALLOW_MODE_B_IN_CI": "1"},
        )
        # Should not fail due to CI guard (may still fail for other reasons,
        # but stderr should NOT contain the CI rejection message)
        assert "not permitted in CI" not in result.stderr, (
            "ALLOW_MODE_B_IN_CI=1 must bypass the CI guard"
        )
        assert "Mode B allowed in CI" in result.stdout, (
            "Must acknowledge Mode B CI override in output"
        )
