"""Tier 0 harness verification tests (WS-ADR-050-001).

These tests verify that ops/scripts/tier0.sh correctly detects failures
and returns appropriate exit codes. Each test corresponds to a Tier 1
verification criterion from WS-ADR-050-001.

Hardening additions (ADR-050 Mode B enforcement):
- Missing tooling is a FAIL unless --allow-missing declares Mode B
- --allow-missing rejected in CI unless ALLOW_MODE_B_IN_CI=1
- Frontend build auto-detects spa/ changes (tracked + untracked)
- Machine-readable JSON with schema_version, timing, exit_code

Performance design:
- Only 3 tests run the full pytest+lint suite (Criteria 1, 2, 6)
- All other tests use --skip-checks pytest,lint to test harness logic only
- Class-level fixtures deduplicate identical harness invocations
- Tests that trigger argument validation failures exit instantly (no checks)

Test approach: subprocess invocation of the harness script with
deliberately introduced violations, verifying exit codes.
"""

import json
import os
import subprocess
import textwrap

import pytest

# Excluded from default runs. Run explicitly: pytest -m slow
pytestmark = pytest.mark.slow

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HARNESS = os.path.join(REPO_ROOT, "ops", "scripts", "tier0.sh")

# Mode B declaration for missing mypy
ALLOW_MISSING_TYPECHECK = ["--allow-missing", "typecheck"]

# Skip expensive checks when testing harness logic only (scope, JSON, Mode B).
# pytest and lint are the expensive checks (~minutes each). Typecheck, frontend,
# and scope are fast or auto-skipped when not triggered.
SKIP_EXPENSIVE = ["--skip-checks", "pytest,lint"]


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


# ===========================================================================
# Full-suite tests: These MUST run pytest/lint to verify detection.
# Only 3 tests in this section — they are the expensive ones.
# ===========================================================================


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


# ===========================================================================
# Harness-logic tests: Skip pytest+lint, test harness behavior only.
# These run in seconds, not minutes.
# ===========================================================================


# ---------------------------------------------------------------------------
# Criterion 3: Missing type checker fails without Mode B declaration
# ---------------------------------------------------------------------------
class TestCriterion3TypeCheckMissing:
    """Without --allow-missing, a missing type checker must cause failure.

    This is the Mode A enforcement: missing tooling is not silently skipped.
    """

    def test_harness_fails_when_typecheck_missing(self):
        # Skip pytest+lint — we only care about typecheck behavior
        result = run_harness(*SKIP_EXPENSIVE)
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
        result = run_harness(*SKIP_EXPENSIVE, *ALLOW_MISSING_TYPECHECK)
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
        # Skip pytest+lint — we only need the frontend check
        result = run_harness(*SKIP_EXPENSIVE, *ALLOW_MISSING_TYPECHECK)
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
        result = run_harness(
            "--scope", "app/", *SKIP_EXPENSIVE, *ALLOW_MISSING_TYPECHECK,
        )
        assert result.returncode != 0, (
            "Tier 0 harness must return non-zero when files outside "
            "declared scope are modified"
        )


# ---------------------------------------------------------------------------
# Machine-readable output: schema contract
# ---------------------------------------------------------------------------
class TestMachineReadableOutput:
    """Verify the harness emits parseable JSON with required fields."""

    @pytest.fixture(autouse=True, scope="class")
    def _shared_harness_run(self, request):
        """Run harness once, share result across tests in this class."""
        request.cls._result = run_harness(
            *SKIP_EXPENSIVE, *ALLOW_MISSING_TYPECHECK,
        )
        request.cls._data = extract_json(request.cls._result.stdout)

    def test_json_schema_version_and_fields(self):
        result = self._result
        data = self._data
        assert "--- TIER0_JSON ---" in result.stdout, (
            "Harness must emit --- TIER0_JSON --- marker"
        )
        assert data is not None, "JSON block must be parseable"

        # schema_version for forward compatibility
        assert data["schema_version"] == 1, (
            "schema_version must be 1"
        )

        # Core fields
        assert data["overall"] in ("PASS", "PASS_WITH_SKIPS", "FAIL")
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
        # Trigger a guaranteed scope failure using the test seam
        result = run_harness(
            "--ws",
            "--scope", "nonexistent/",
            *SKIP_EXPENSIVE,
            *ALLOW_MISSING_TYPECHECK,
            env_override={
                "TIER0_CHANGED_FILES_OVERRIDE": "app/main.py",
            },
        )
        data = extract_json(result.stdout)
        assert data is not None, (
            "JSON must be emitted even on FAIL — downstream tools need it"
        )
        assert data["overall"] == "FAIL"
        assert data["exit_code"] != 0


# ---------------------------------------------------------------------------
# Criterion 7: SKIP is not PASS — summary distinguishes them
# ---------------------------------------------------------------------------
class TestCriterion7SkipIsNotPass:
    """When checks are skipped, harness must NOT say ALL CHECKS PASSED."""

    @pytest.fixture(autouse=True, scope="class")
    def _shared_harness_run(self, request):
        """Run harness once, share result across tests in this class."""
        request.cls._result = run_harness(
            *SKIP_EXPENSIVE, *ALLOW_MISSING_TYPECHECK,
        )
        request.cls._data = extract_json(request.cls._result.stdout)

    def test_mode_b_skip_produces_passed_with_skips(self):
        """Mode B typecheck skip -> PASSED WITH SKIPS, not ALL CHECKS PASSED."""
        result = self._result
        data = self._data

        if data and data["checks"]["typecheck"] == "PASS":
            pytest.skip("mypy is installed — no skip to test")

        assert "ALL CHECKS PASSED" not in result.stdout, (
            "Harness must not say ALL CHECKS PASSED when checks were skipped"
        )
        assert "PASSED WITH SKIPS" in result.stdout, (
            "Harness must say PASSED WITH SKIPS when checks were skipped"
        )
        assert data is not None
        assert data["overall"] == "PASS_WITH_SKIPS", (
            "JSON overall must be PASS_WITH_SKIPS when checks skipped"
        )

    def test_all_checks_passed_requires_zero_skips(self):
        """ALL CHECKS PASSED should only appear when every check actually ran."""
        result = self._result
        data = self._data

        if data and data["overall"] == "PASS":
            # Genuine full pass — ALL CHECKS PASSED is correct
            assert "ALL CHECKS PASSED" in result.stdout
        else:
            # Something was skipped or failed — must not say ALL CHECKS PASSED
            assert "ALL CHECKS PASSED" not in result.stdout


# ---------------------------------------------------------------------------
# CI guard: --allow-missing rejected under CI=true
# ---------------------------------------------------------------------------
class TestCIGuard:
    """In CI, --allow-missing must be rejected unless ALLOW_MODE_B_IN_CI=1."""

    def test_ci_rejects_allow_missing(self):
        # CI guard exits before running any checks — already fast
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
            *SKIP_EXPENSIVE,
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


# ==========================================================================
# WS-TIER0-SCOPE-001: Work Statement mode scope enforcement
#
# Criteria 1-7 from WS-TIER0-SCOPE-001. These tests must all FAIL before
# implementation and PASS after.
#
# Test seam: TIER0_CHANGED_FILES_OVERRIDE env var controls which files
# appear as "changed" without depending on real git state.
# ==========================================================================


# ---------------------------------------------------------------------------
# WS Criterion 1: --ws flag without --scope must fail
# ---------------------------------------------------------------------------
class TestWSCriterion1FlagRequiresScope:
    """Invoke tier0 with --ws and no --scope -> exit non-zero, stderr has
    actionable error instructing how to pass scope."""

    @pytest.fixture(autouse=True, scope="class")
    def _shared_harness_run(self, request):
        """--ws without --scope exits immediately — one invocation for both tests."""
        request.cls._result = run_harness("--ws", *ALLOW_MISSING_TYPECHECK)

    def test_ws_flag_without_scope_fails(self):
        assert self._result.returncode != 0, (
            "WS mode (--ws) without --scope must return non-zero"
        )

    def test_ws_flag_without_scope_has_actionable_error(self):
        combined = self._result.stdout + self._result.stderr
        assert "--scope" in combined, (
            "Error message must mention --scope so the user knows how to fix it"
        )


# ---------------------------------------------------------------------------
# WS Criterion 2: COMBINE_WS_ID env var without --scope must fail
# ---------------------------------------------------------------------------
class TestWSCriterion2EnvVarRequiresScope:
    """Invoke tier0 with COMBINE_WS_ID=WS-123 and no --scope -> fail."""

    def test_ws_env_var_without_scope_fails(self):
        # Exits immediately at WS scope guard — already fast
        result = run_harness(
            *ALLOW_MISSING_TYPECHECK,
            env_override={"COMBINE_WS_ID": "WS-TIER0-SCOPE-001"},
        )
        assert result.returncode != 0, (
            "WS mode (COMBINE_WS_ID) without --scope must return non-zero"
        )


# ---------------------------------------------------------------------------
# WS Criterion 3: WS mode scope PASS
# ---------------------------------------------------------------------------
class TestWSCriterion3ScopePass:
    """With scope paths covering the changed-file set, tier0 returns success
    and JSON shows checks.scope=PASS."""

    def test_ws_mode_scope_pass(self):
        # Use test seam to control changed files; skip expensive checks
        result = run_harness(
            "--ws",
            "--scope", "ops/scripts/", "tests/infrastructure/",
            *SKIP_EXPENSIVE,
            *ALLOW_MISSING_TYPECHECK,
            env_override={
                "TIER0_CHANGED_FILES_OVERRIDE": "ops/scripts/tier0.sh\ntests/infrastructure/test_tier0_harness.py",
            },
        )
        assert result.returncode == 0, (
            f"WS mode with scope covering all changed files must return zero.\n"
            f"stdout: {result.stdout[-500:]}\nstderr: {result.stderr[-500:]}"
        )
        data = extract_json(result.stdout)
        assert data is not None
        assert data["checks"]["scope"] == "PASS", (
            "checks.scope must be PASS when all changed files are in scope"
        )


# ---------------------------------------------------------------------------
# WS Criterion 4: WS mode scope FAIL
# ---------------------------------------------------------------------------
class TestWSCriterion4ScopeFail:
    """With at least one changed file outside scope, tier0 fails and JSON
    shows checks.scope=FAIL, stderr lists out-of-scope files."""

    @pytest.fixture(autouse=True, scope="class")
    def _shared_harness_run(self, request):
        """One invocation for both scope-fail assertions."""
        request.cls._result = run_harness(
            "--ws",
            "--scope", "ops/scripts/",
            *SKIP_EXPENSIVE,
            *ALLOW_MISSING_TYPECHECK,
            env_override={
                "TIER0_CHANGED_FILES_OVERRIDE": "ops/scripts/tier0.sh\napp/main.py",
            },
        )
        request.cls._data = extract_json(request.cls._result.stdout)

    def test_ws_mode_scope_fail(self):
        assert self._result.returncode != 0, (
            "WS mode with out-of-scope files must return non-zero"
        )
        assert self._data is not None
        assert self._data["checks"]["scope"] == "FAIL", (
            "checks.scope must be FAIL when files are out of scope"
        )

    def test_ws_mode_scope_fail_lists_files(self):
        combined = self._result.stdout + self._result.stderr
        assert "app/main.py" in combined, (
            "Out-of-scope files must be listed in output"
        )


# ---------------------------------------------------------------------------
# WS Criterion 5: Non-WS mode scope remains SKIPPED
# ---------------------------------------------------------------------------
class TestWSCriterion5NonWSModeSkipped:
    """Run tier0 without --ws and without scopes -> does not fail due to scope;
    JSON includes ws_mode=false and checks.scope=SKIPPED."""

    @pytest.fixture(autouse=True, scope="class")
    def _shared_harness_run(self, request):
        """One invocation for both non-WS-mode assertions."""
        request.cls._result = run_harness(
            *SKIP_EXPENSIVE, *ALLOW_MISSING_TYPECHECK,
        )
        request.cls._data = extract_json(request.cls._result.stdout)

    def test_non_ws_mode_scope_skipped(self):
        data = self._data
        assert data is not None
        assert data.get("ws_mode") is False, (
            "ws_mode must be false when not in WS mode"
        )
        assert data["checks"]["scope"] in ("SKIP", "SKIPPED"), (
            "checks.scope must be SKIP or SKIPPED when not in WS mode"
        )

    def test_non_ws_mode_does_not_fail_on_scope(self):
        """Non-WS mode must not fail due to missing scope."""
        if self._result.returncode != 0:
            data = self._data
            assert data is None or data["checks"]["scope"] != "FAIL", (
                "Non-WS mode must not fail due to scope"
            )


# ---------------------------------------------------------------------------
# WS Criterion 6: JSON contract (ws_mode, declared_scope_paths, checks.scope)
# ---------------------------------------------------------------------------
class TestWSCriterion6JSONContract:
    """JSON output includes ws_mode (boolean), declared_scope_paths (array),
    and checks.scope (PASS/FAIL/SKIPPED) in all modes."""

    @pytest.fixture(autouse=True, scope="class")
    def _shared_harness_runs(self, request):
        """Two invocations: non-WS mode and WS mode. Shared across 3 tests."""
        request.cls._non_ws_result = run_harness(
            *SKIP_EXPENSIVE, *ALLOW_MISSING_TYPECHECK,
        )
        request.cls._non_ws_data = extract_json(
            request.cls._non_ws_result.stdout,
        )
        request.cls._ws_result = run_harness(
            "--ws",
            "--scope", "ops/scripts/", "tests/",
            *SKIP_EXPENSIVE,
            *ALLOW_MISSING_TYPECHECK,
            env_override={
                "TIER0_CHANGED_FILES_OVERRIDE": "ops/scripts/tier0.sh",
            },
        )
        request.cls._ws_data = extract_json(request.cls._ws_result.stdout)

    def test_json_has_ws_fields_in_non_ws_mode(self):
        data = self._non_ws_data
        assert data is not None
        assert "ws_mode" in data, "JSON must include ws_mode in non-WS mode"
        assert isinstance(data["ws_mode"], bool), "ws_mode must be boolean"
        assert "declared_scope_paths" in data, (
            "JSON must include declared_scope_paths in non-WS mode"
        )
        assert isinstance(data["declared_scope_paths"], list), (
            "declared_scope_paths must be an array"
        )

    def test_json_has_ws_fields_in_ws_mode(self):
        data = self._ws_data
        assert data is not None
        assert data["ws_mode"] is True, "ws_mode must be true in WS mode"
        assert data["declared_scope_paths"] == ["ops/scripts/", "tests/"], (
            "declared_scope_paths must match --scope arguments"
        )
        assert data["checks"]["scope"] in ("PASS", "FAIL"), (
            "checks.scope must be PASS or FAIL (never SKIPPED) in WS mode"
        )

    def test_scope_check_values_valid(self):
        """checks.scope must be PASS, FAIL, or SKIP/SKIPPED."""
        data = self._non_ws_data
        assert data is not None
        assert data["checks"]["scope"] in ("PASS", "FAIL", "SKIP", "SKIPPED"), (
            f"checks.scope has unexpected value: {data['checks']['scope']}"
        )


# ---------------------------------------------------------------------------
# WS Criterion 7: CI guard for WS mode scope
# ---------------------------------------------------------------------------
class TestWSCriterion7CIGuard:
    """If CI=true and WS mode is active, scope is mandatory with no override
    unless ALLOW_SCOPE_SKIP_IN_CI=1."""

    def test_ci_ws_mode_requires_scope(self):
        # Exits immediately at WS scope guard — already fast
        result = run_harness(
            "--ws",
            env_override={
                "CI": "true",
                "TIER0_CHANGED_FILES_OVERRIDE": "ops/scripts/tier0.sh",
            },
        )
        assert result.returncode != 0, (
            "CI + WS mode without --scope must fail"
        )

    def test_ci_ws_mode_scope_override(self):
        """ALLOW_SCOPE_SKIP_IN_CI=1 bypasses the CI scope requirement."""
        result = run_harness(
            "--ws",
            *SKIP_EXPENSIVE,
            *ALLOW_MISSING_TYPECHECK,
            env_override={
                "CI": "true",
                "ALLOW_MODE_B_IN_CI": "1",
                "ALLOW_SCOPE_SKIP_IN_CI": "1",
                "TIER0_CHANGED_FILES_OVERRIDE": "ops/scripts/tier0.sh",
            },
        )
        # Should not exit immediately due to WS scope guard
        # (It may still fail for other reasons, but not from "WS mode requires --scope")
        assert "WS mode requires --scope" not in result.stderr, (
            "ALLOW_SCOPE_SKIP_IN_CI=1 must bypass the WS scope requirement"
        )
