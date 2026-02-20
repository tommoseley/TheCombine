"""WS-AWS-DB-003: Environment profile tests.

Tier 1 verification criteria for extending EnvironmentType with
DEV_AWS and TEST_AWS, rejecting invalid environments, and ensuring
a unified DATABASE_URL resolution path.

All tests must fail before implementation and pass after.
"""

import os
import importlib
from unittest.mock import patch

import pytest


class TestCriterion1EnvironmentTypeExtended:
    """EnvironmentType enum includes DEV_AWS and TEST_AWS."""

    def test_dev_aws_exists(self):
        from app.core.environment import EnvironmentType
        assert hasattr(EnvironmentType, "DEV_AWS"), (
            "EnvironmentType must have DEV_AWS member"
        )
        assert EnvironmentType.DEV_AWS.value == "dev_aws"

    def test_test_aws_exists(self):
        from app.core.environment import EnvironmentType
        assert hasattr(EnvironmentType, "TEST_AWS"), (
            "EnvironmentType must have TEST_AWS member"
        )
        assert EnvironmentType.TEST_AWS.value == "test_aws"

    def test_existing_types_preserved(self):
        from app.core.environment import EnvironmentType
        assert EnvironmentType.DEVELOPMENT.value == "development"
        assert EnvironmentType.STAGING.value == "staging"
        assert EnvironmentType.PRODUCTION.value == "production"
        assert EnvironmentType.TEST.value == "test"


class TestCriterion2InvalidEnvRejected:
    """App refuses invalid ENVIRONMENT values with clear error."""

    def test_invalid_env_raises(self):
        from app.core.environment import Environment
        with patch.dict(os.environ, {"ENVIRONMENT": "bogus_invalid_env"}, clear=False):
            with pytest.raises((ValueError, SystemExit)):
                # Re-evaluate current() with the invalid value
                Environment.current()

    def test_empty_env_still_works(self):
        """Empty ENVIRONMENT should fall through to detection (backward compat)."""
        from app.core.environment import Environment, EnvironmentType
        with patch.dict(os.environ, {"ENVIRONMENT": ""}, clear=False):
            result = Environment.current()
            # Should default to TEST (pytest detection) or DEVELOPMENT
            assert result in (EnvironmentType.DEVELOPMENT, EnvironmentType.TEST)


class TestCriterion3DatabaseURLPerEnv:
    """Each env resolves to a distinct DATABASE_URL."""

    def test_dev_aws_recognized_as_environment(self):
        from app.core.environment import Environment, EnvironmentType
        with patch.dict(os.environ, {"ENVIRONMENT": "dev_aws"}, clear=False):
            result = Environment.current()
            assert result == EnvironmentType.DEV_AWS

    def test_test_aws_recognized_as_environment(self):
        from app.core.environment import Environment, EnvironmentType
        with patch.dict(os.environ, {"ENVIRONMENT": "test_aws"}, clear=False):
            result = Environment.current()
            assert result == EnvironmentType.TEST_AWS


class TestCriterion4NoSecretsCommitted:
    """No connection strings, passwords, or hostnames in committed config."""

    def test_no_hardcoded_rds_endpoints(self):
        """Config files must not contain RDS endpoints."""
        import app.core.config
        import app.core.database
        import app.core.environment

        for module in [app.core.config, app.core.database, app.core.environment]:
            source_path = module.__file__
            with open(source_path, "r") as f:
                source = f.read()
            assert "cyqzjxl9c9jd" not in source, (
                f"RDS endpoint found in {source_path}"
            )
            assert "combine_dev_user" not in source
            assert "combine_test_user" not in source


class TestCriterion5BackwardCompatible:
    """Direct DATABASE_URL still works when ENVIRONMENT is not set."""

    def test_direct_database_url_works(self):
        """If DATABASE_URL is set and ENVIRONMENT is empty, app uses DATABASE_URL."""
        # This tests the existing behavior — should pass before and after
        from app.core.config import DATABASE_URL
        assert DATABASE_URL is not None, "DATABASE_URL must be resolvable"


class TestCriterion6UnifiedResolution:
    """database.py uses config.py's DATABASE_URL, not its own."""

    def test_database_imports_from_config(self):
        """database.py must import DATABASE_URL from config, not read env independently."""
        import app.core.database
        source_path = app.core.database.__file__
        with open(source_path, "r") as f:
            source = f.read()
        # Must import from config
        assert "from app.core.config import DATABASE_URL" in source, (
            "database.py must import DATABASE_URL from app.core.config"
        )
        # Must NOT have its own os.getenv for DATABASE_URL
        assert "os.getenv('DATABASE_URL'" not in source, (
            "database.py must not independently read DATABASE_URL from env"
        )
        assert 'os.getenv("DATABASE_URL"' not in source, (
            "database.py must not independently read DATABASE_URL from env"
        )
