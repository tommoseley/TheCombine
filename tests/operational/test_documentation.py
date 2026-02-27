"""Tests for documentation completeness."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestDocumentationExists:
    """Verify required documentation exists."""
    
    def test_readme_exists(self):
        """README.md exists."""
        assert (PROJECT_ROOT / "README.md").exists()
    
    def test_configuration_doc_exists(self):
        """CONFIGURATION.md exists."""
        assert (PROJECT_ROOT / "docs" / "CONFIGURATION.md").exists()
    
    def test_runbook_exists(self):
        """RUNBOOK.md exists."""
        assert (PROJECT_ROOT / "docs" / "RUNBOOK.md").exists()
    
    def test_deployment_checklist_exists(self):
        """DEPLOYMENT-CHECKLIST.md exists."""
        assert (PROJECT_ROOT / "docs" / "DEPLOYMENT-CHECKLIST.md").exists()
    
    def test_staging_deployment_exists(self):
        """STAGING-DEPLOYMENT.md exists."""
        assert (PROJECT_ROOT / "docs" / "STAGING-DEPLOYMENT.md").exists()


class TestConfigurationDocCompleteness:
    """Verify configuration documentation is complete."""
    
    def test_documents_database_url(self):
        """DATABASE_URL is documented."""
        content = (PROJECT_ROOT / "docs" / "CONFIGURATION.md").read_text()
        assert "DATABASE_URL" in content
    
    def test_documents_secret_key(self):
        """SECRET_KEY is documented."""
        content = (PROJECT_ROOT / "docs" / "CONFIGURATION.md").read_text()
        assert "SECRET_KEY" in content
    
    def test_documents_oauth(self):
        """OAuth variables are documented."""
        content = (PROJECT_ROOT / "docs" / "CONFIGURATION.md").read_text()
        assert "GOOGLE_CLIENT_ID" in content
        assert "MICROSOFT_CLIENT_ID" in content
    
    def test_documents_logging(self):
        """Logging variables are documented."""
        content = (PROJECT_ROOT / "docs" / "CONFIGURATION.md").read_text()
        assert "LOG_LEVEL" in content
        assert "LOG_FORMAT" in content


class TestRunbookCompleteness:
    """Verify runbook covers key scenarios."""
    
    def test_health_endpoints_documented(self):
        """Health endpoints are documented."""
        content = (PROJECT_ROOT / "docs" / "RUNBOOK.md").read_text()
        assert "/health" in content
        assert "/health/ready" in content
    
    def test_database_troubleshooting(self):
        """Database troubleshooting is documented."""
        content = (PROJECT_ROOT / "docs" / "RUNBOOK.md").read_text()
        assert "Database" in content
        assert "pg_dump" in content or "backup" in content.lower()
    
    def test_rollback_procedure(self):
        """Rollback procedure is documented."""
        content = (PROJECT_ROOT / "docs" / "RUNBOOK.md").read_text()
        assert "Rollback" in content