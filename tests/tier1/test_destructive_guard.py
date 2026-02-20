"""WS-AWS-DB-005: Destructive action guardrail tests.

Tests the db_destructive_guard.sh require_confirmation function.
Uses a small test harness that sources the guard and calls it.
"""

import os
import subprocess

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GUARD_SCRIPT = os.path.join(REPO_ROOT, "ops", "scripts", "db_destructive_guard.sh")


def run_guard(target_env, env_override=None):
    """Run the guard function in a subprocess."""
    env = os.environ.copy()
    env.pop("CI", None)
    env.pop("CONFIRM_ENV", None)
    env.pop("ALLOW_DESTRUCTIVE_IN_CI", None)
    if env_override:
        env.update(env_override)

    # Inline bash script that sources the guard and calls require_confirmation
    test_script = f"""
        source "{GUARD_SCRIPT}"
        require_confirmation "{target_env}" "test destructive action"
    """
    return subprocess.run(
        ["bash", "-c", test_script],
        capture_output=True,
        text=True,
        env=env,
    )


class TestCriterion1ConfirmationRequired:
    """Destructive actions require CONFIRM_ENV=<env_name>."""

    def test_correct_confirmation_succeeds(self):
        result = run_guard("dev", {"CONFIRM_ENV": "dev"})
        assert result.returncode == 0, (
            f"Correct CONFIRM_ENV should succeed.\nstderr: {result.stderr}"
        )
        assert "Confirmed" in result.stdout


class TestCriterion2WrongConfirmationRejected:
    """CONFIRM_ENV=test when targeting dev -> fails."""

    def test_wrong_env_rejected(self):
        result = run_guard("dev", {"CONFIRM_ENV": "test"})
        assert result.returncode != 0
        assert "mismatch" in result.stderr.lower()


class TestCriterion3MissingConfirmationRejected:
    """Running without CONFIRM_ENV -> fails with clear error."""

    def test_missing_confirm_env_fails(self):
        result = run_guard("dev")
        assert result.returncode != 0
        assert "CONFIRM_ENV" in result.stderr

    def test_error_shows_required_value(self):
        result = run_guard("test")
        assert result.returncode != 0
        assert "CONFIRM_ENV=test" in result.stderr

    def test_wildcard_rejected(self):
        result = run_guard("dev", {"CONFIRM_ENV": "*"})
        assert result.returncode != 0
        assert "not permitted" in result.stderr.lower()

    def test_all_rejected(self):
        result = run_guard("dev", {"CONFIRM_ENV": "all"})
        assert result.returncode != 0
        assert "not permitted" in result.stderr.lower()


class TestCriterion4CIGuard:
    """CI=true + destructive actions fail unless ALLOW_DESTRUCTIVE_IN_CI=1."""

    def test_ci_blocks_destructive(self):
        result = run_guard("dev", {"CI": "true", "CONFIRM_ENV": "dev"})
        assert result.returncode != 0
        assert "ALLOW_DESTRUCTIVE_IN_CI" in result.stderr

    def test_ci_allows_with_override(self):
        result = run_guard("dev", {
            "CI": "true",
            "CONFIRM_ENV": "dev",
            "ALLOW_DESTRUCTIVE_IN_CI": "1",
        })
        assert result.returncode == 0


class TestCriterion5NonDestructiveUnaffected:
    """Normal migrations (upgrade) and reads do not require CONFIRM_ENV."""

    def test_migrate_does_not_require_confirm(self):
        """db_migrate.sh does not source the guard — no CONFIRM_ENV needed."""
        migrate_script = os.path.join(REPO_ROOT, "ops", "scripts", "db_migrate.sh")
        with open(migrate_script, "r") as f:
            source = f.read()
        assert "db_destructive_guard" not in source, (
            "db_migrate.sh must not source the destructive guard"
        )

    def test_connect_does_not_require_confirm(self):
        """db_connect.sh does not source the guard."""
        connect_script = os.path.join(REPO_ROOT, "ops", "scripts", "db_connect.sh")
        with open(connect_script, "r") as f:
            source = f.read()
        assert "db_destructive_guard" not in source

    def test_reset_does_require_confirm(self):
        """db_reset.sh must source the destructive guard."""
        reset_script = os.path.join(REPO_ROOT, "ops", "scripts", "db_reset.sh")
        with open(reset_script, "r") as f:
            source = f.read()
        assert "db_destructive_guard" in source
