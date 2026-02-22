"""Smoke tests for The Combine."""

import pytest
from pathlib import Path


class TestApplicationSmoke:
    """Basic smoke tests to verify application can start."""
    
    def test_app_module_imports(self):
        """Core app modules can be imported."""
        from app.core import config
        from app.api import api_router
        assert config is not None
        assert api_router is not None
    
    def test_execution_module_imports(self):
        """Execution module imports."""
        from app.execution import (
            ExecutionContext,
            LLMStepExecutor,
            WorkflowLoader,
        )
        assert ExecutionContext is not None
        assert LLMStepExecutor is not None
        assert WorkflowLoader is not None
    
    def test_llm_module_imports(self):
        """LLM module imports."""
        from app.llm import (
            MockLLMProvider,
            PromptBuilder,
        )
        assert MockLLMProvider is not None
        assert PromptBuilder is not None
    
    def test_persistence_module_imports(self):
        """Persistence module imports."""
        from app.persistence import (
            InMemoryDocumentRepository,
        )
        assert InMemoryDocumentRepository is not None
    
    def test_observability_module_imports(self):
        """Observability module imports."""
        from app.observability import (
            MetricsCollector,
            HealthChecker,
        )
        assert MetricsCollector is not None
        assert HealthChecker is not None


class TestConfigurationSmoke:
    """Smoke tests for configuration files."""
    
    def test_dockerfile_exists(self):
        """Dockerfile exists."""
        assert Path("Dockerfile").exists()
    
    def test_requirements_exists(self):
        """requirements.txt exists."""
        assert Path("requirements.txt").exists()
    
    def test_docker_compose_exists(self):
        """docker-compose.yml exists."""
        assert Path("docker-compose.yml").exists()


class TestCombineConfigSmoke:
    """Smoke tests for combine-config data."""

    def test_workflows_directory_exists(self):
        """Workflows directory exists."""
        assert Path("combine-config/workflows").exists()

    def test_schemas_directory_exists(self):
        """Schemas directory exists."""
        assert Path("combine-config/schemas").exists()

    def test_prompts_directory_exists(self):
        """Prompts directory exists."""
        assert Path("combine-config/prompts/tasks").exists()

    def test_active_releases_exists(self):
        """Active releases config exists."""
        assert Path("combine-config/_active/active_releases.json").exists()


class TestHealthEndpointSmoke:
    """Smoke tests for health infrastructure."""
    
    @pytest.mark.asyncio
    async def test_health_checker_works(self):
        """Health checker can run checks."""
        from app.observability import HealthChecker, HealthStatus, ComponentHealth
        
        checker = HealthChecker(version="test")
        
        async def simple_check():
            return ComponentHealth(name="test", status=HealthStatus.HEALTHY)
        
        checker.register("test", simple_check)
        health = await checker.check_all()
        
        assert health.status == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_metrics_collector_works(self):
        """Metrics collector records metrics."""
        from app.observability import MetricsCollector
        from decimal import Decimal
        
        collector = MetricsCollector()
        collector.record_execution_start("test-workflow")
        collector.record_llm_call(100, 50, 500.0, Decimal("0.01"))
        
        metrics = collector.get_metrics()
        
        assert metrics.executions_started == 1
        assert metrics.llm_calls_total == 1

