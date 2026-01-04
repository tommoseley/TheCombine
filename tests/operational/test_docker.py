"""Operational tests for Docker configuration."""

import pytest
import yaml
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestDockerCompose:
    """Tests for docker-compose files."""
    
    def test_docker_compose_valid_yaml(self):
        """docker-compose.yml is valid YAML."""
        compose_file = PROJECT_ROOT / "docker-compose.yml"
        
        assert compose_file.exists(), "docker-compose.yml not found"
        
        with open(compose_file) as f:
            data = yaml.safe_load(f)
        
        assert "services" in data
        assert "app" in data["services"]
    
    def test_docker_compose_staging_valid_yaml(self):
        """docker-compose.staging.yml is valid YAML."""
        compose_file = PROJECT_ROOT / "docker-compose.staging.yml"
        
        assert compose_file.exists(), "docker-compose.staging.yml not found"
        
        with open(compose_file) as f:
            data = yaml.safe_load(f)
        
        assert "services" in data
    
    def test_docker_compose_has_health_check(self):
        """App service has health check configured."""
        compose_file = PROJECT_ROOT / "docker-compose.yml"
        
        with open(compose_file) as f:
            data = yaml.safe_load(f)
        
        app_service = data["services"]["app"]
        assert "healthcheck" in app_service
        assert "test" in app_service["healthcheck"]
    
    def test_docker_compose_db_has_health_check(self):
        """DB service has health check configured."""
        compose_file = PROJECT_ROOT / "docker-compose.yml"
        
        with open(compose_file) as f:
            data = yaml.safe_load(f)
        
        db_service = data["services"]["db"]
        assert "healthcheck" in db_service
    
    def test_staging_removes_dev_volumes(self):
        """Staging compose removes development volumes."""
        compose_file = PROJECT_ROOT / "docker-compose.staging.yml"
        
        with open(compose_file) as f:
            data = yaml.safe_load(f)
        
        app_service = data["services"]["app"]
        # Should have empty volumes list to override dev mounts
        assert app_service.get("volumes") == []


class TestDockerfile:
    """Tests for Dockerfile."""
    
    def test_dockerfile_exists(self):
        """Dockerfile exists."""
        dockerfile = PROJECT_ROOT / "Dockerfile"
        assert dockerfile.exists()
    
    def test_dockerfile_has_healthcheck(self):
        """Dockerfile has HEALTHCHECK instruction."""
        dockerfile = PROJECT_ROOT / "Dockerfile"
        
        content = dockerfile.read_text()
        assert "HEALTHCHECK" in content
    
    def test_dockerfile_uses_non_root_user(self):
        """Dockerfile runs as non-root user."""
        dockerfile = PROJECT_ROOT / "Dockerfile"
        
        content = dockerfile.read_text()
        assert "USER" in content
        # Should have useradd or similar
        assert "appuser" in content.lower() or "nonroot" in content.lower()
    
    def test_dockerfile_exposes_port(self):
        """Dockerfile exposes correct port."""
        dockerfile = PROJECT_ROOT / "Dockerfile"
        
        content = dockerfile.read_text()
        assert "EXPOSE 8000" in content


class TestEnvExample:
    """Tests for .env.example file."""
    
    def test_env_example_exists(self):
        """.env.example exists."""
        env_file = PROJECT_ROOT / ".env.example"
        assert env_file.exists()
    
    def test_env_example_has_required_vars(self):
        """.env.example documents required vars."""
        env_file = PROJECT_ROOT / ".env.example"
        
        content = env_file.read_text()
        
        required = [
            "DATABASE_URL",
            "SECRET_KEY",
            "ANTHROPIC_API_KEY",
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET",
        ]
        
        for var in required:
            assert var in content, f"{var} not documented in .env.example"
    
    def test_env_example_has_oauth_vars(self):
        """.env.example documents OAuth vars."""
        env_file = PROJECT_ROOT / ".env.example"
        
        content = env_file.read_text()
        
        assert "GOOGLE_CLIENT_ID" in content
        assert "MICROSOFT_CLIENT_ID" in content
