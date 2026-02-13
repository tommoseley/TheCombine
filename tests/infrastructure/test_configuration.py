"""Tests for infrastructure configuration."""

import pytest
import json
from pathlib import Path


class TestDeploymentConfiguration:
    """Tests for deployment configuration files."""
    
    def test_dockerfile_exists(self):
        """Dockerfile exists."""
        assert Path("Dockerfile").exists()
    
    def test_docker_compose_exists(self):
        """docker-compose.yml exists."""
        assert Path("docker-compose.yml").exists()
    
    def test_github_workflow_exists(self):
        """GitHub Actions deploy workflow exists."""
        assert Path(".github/workflows/deploy.yml").exists()
    
    def test_deploy_workflow_has_ecs(self):
        """Deploy workflow uses ECS."""
        content = Path(".github/workflows/deploy.yml").read_text(encoding="utf-8-sig")
        assert "ECS_CLUSTER" in content
        assert "ECS_SERVICE" in content


class TestOpsScripts:
    """Tests for ops scripts."""
    
    OPS_DIR = Path("ops")
    
    def test_ops_directory_exists(self):
        """ops/ directory exists."""
        assert self.OPS_DIR.exists()
    
    def test_aws_scripts_exist(self):
        """AWS ops scripts exist."""
        aws_dir = self.OPS_DIR / "aws"
        assert aws_dir.exists()
        assert (aws_dir / "task-definition.json").exists()
    
    def test_db_scripts_exist(self):
        """Database scripts exist."""
        db_dir = self.OPS_DIR / "db"
        assert db_dir.exists()
        assert (db_dir / "schema.sql").exists() or (db_dir / "schema_clean.sql").exists()


class TestSchemaFiles:
    """Tests for JSON schema files."""
    
    SCHEMAS_DIR = Path("seed/schemas/strategy")
    REQUIRED_SCHEMAS = [
        "project-discovery.json",
        "requirements-doc.json",
        "architecture-doc.json",
        "strategy-review.json",
    ]
    
    def test_schemas_directory_exists(self):
        """Schemas directory exists."""
        assert self.SCHEMAS_DIR.exists(), "seed/schemas/strategy/ not found"
    
    def test_required_schemas_exist(self):
        """All required schema files exist."""
        for filename in self.REQUIRED_SCHEMAS:
            path = self.SCHEMAS_DIR / filename
            assert path.exists(), f"Missing schema: {filename}"
    
    @pytest.mark.parametrize("schema_file", REQUIRED_SCHEMAS)
    def test_schemas_are_valid_json(self, schema_file):
        """Schema files are valid JSON."""
        path = self.SCHEMAS_DIR / schema_file
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        assert isinstance(data, dict)
    
    @pytest.mark.parametrize("schema_file", REQUIRED_SCHEMAS)
    def test_schemas_have_type(self, schema_file):
        """Schema files have type definition."""
        path = self.SCHEMAS_DIR / schema_file
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        assert "type" in data


class TestPromptFiles:
    """Tests for task prompt files."""
    
    PROMPTS_DIR = Path("seed/prompts/tasks")
    REQUIRED_PROMPTS = [
        "strategy-discovery-v1.txt",
        "strategy-requirements-v1.txt",
        "strategy-architecture-v1.txt",
        "strategy-review-v1.txt",
    ]
    
    def test_prompts_directory_exists(self):
        """Prompts directory exists."""
        assert self.PROMPTS_DIR.exists(), "seed/prompts/tasks/ not found"
    
    def test_required_prompts_exist(self):
        """All required prompt files exist."""
        for filename in self.REQUIRED_PROMPTS:
            path = self.PROMPTS_DIR / filename
            assert path.exists(), f"Missing prompt: {filename}"
    
    @pytest.mark.parametrize("prompt_file", REQUIRED_PROMPTS)
    def test_prompts_not_empty(self, prompt_file):
        """Prompt files are not empty."""
        path = self.PROMPTS_DIR / prompt_file
        content = path.read_text(encoding="utf-8-sig")
        assert len(content.strip()) > 100, f"Prompt too short: {prompt_file}"
    
    @pytest.mark.parametrize("prompt_file", REQUIRED_PROMPTS)
    def test_prompts_have_instructions(self, prompt_file):
        """Prompt files contain instructions."""
        path = self.PROMPTS_DIR / prompt_file
        content = path.read_text(encoding="utf-8-sig").lower()
        assert "instruction" in content or "output" in content or "json" in content

