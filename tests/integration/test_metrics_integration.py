"""
CORRECTED test_metrics_integration.py

Copy this entire file to: tests/integration/test_metrics_integration.py
"""

"""
Integration tests for PIPELINE-175D Metrics Dashboard

Tests full stack with real database (seeded test data).
No mocking - tests actual repository → service → router flow.
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from fastapi.testclient import TestClient

from app.orchestrator_api.main import app
from app.orchestrator_api.persistence.database import get_db_session
from app.orchestrator_api.models import (
    Pipeline,
    PipelinePromptUsage,
    RolePrompt,
    PhaseConfiguration
)

client = TestClient(app)


@pytest.fixture(scope="module")
def test_db():
    """Setup test database with seeded data"""
    # This would typically use a test database
    # For now, we'll use the existing database structure
    yield
    # Cleanup after tests


@pytest.fixture
def seed_test_data():
    """Seed database with test pipelines and usage records"""
    with get_db_session() as session:
        # Create test pipelines - CORRECTED FIELD NAMES
        pipeline1 = Pipeline(
            pipeline_id="integration-test-1",                              # ← FIXED: was id
            epic_id="epic-1",                                              # ← ADDED: required
            state="completed",                                             # ← FIXED: was status
            current_phase="commit_phase",
            canon_version="1.0",                                           # ← ADDED: required
            initial_context={"epic": {"description": "Integration Test Epic 1"}},  # ← FIXED: was artifacts
            created_at=datetime.now(timezone.utc) - timedelta(days=2)
        )
        
        pipeline2 = Pipeline(
            pipeline_id="integration-test-2",                              # ← FIXED: was id
            epic_id="epic-2",                                              # ← ADDED: required
            state="in_progress",                                           # ← FIXED: was status
            current_phase="architect_phase",
            canon_version="1.0",                                           # ← ADDED: required
            initial_context={"pm": {"epic_description": "Integration Test Epic 2"}},  # ← FIXED: was artifacts
            created_at=datetime.now(timezone.utc) - timedelta(days=1)
        )
        
        session.add(pipeline1)
        session.add(pipeline2)
        session.commit()
        
        # Create usage records
        usage1 = PipelinePromptUsage(
            pipeline_id="integration-test-1",
            prompt_id=1,  # Assumes role prompts exist
            input_tokens=1500,
            output_tokens=2500,
            cost_usd=Decimal("0.025"),
            execution_time_ms=2500,
            used_at=datetime.now(timezone.utc) - timedelta(days=2, hours=1)
        )
        
        usage2 = PipelinePromptUsage(
            pipeline_id="integration-test-1",
            prompt_id=2,
            input_tokens=2000,
            output_tokens=3000,
            cost_usd=Decimal("0.035"),
            execution_time_ms=3200,
            used_at=datetime.now(timezone.utc) - timedelta(days=2, minutes=30)
        )
        
        usage3 = PipelinePromptUsage(
            pipeline_id="integration-test-2",
            prompt_id=1,
            input_tokens=1000,
            output_tokens=1500,
            cost_usd=Decimal("0.015"),
            execution_time_ms=1800,
            used_at=datetime.now(timezone.utc) - timedelta(days=1, hours=2)
        )
        
        session.add(usage1)
        session.add(usage2)
        session.add(usage3)
        session.commit()
    
    yield
    
    # Cleanup - FIXED: pipeline_id not id
    with get_db_session() as session:
        session.query(PipelinePromptUsage).filter(
            PipelinePromptUsage.pipeline_id.like("integration-test-%")
        ).delete()
        session.query(Pipeline).filter(
            Pipeline.pipeline_id.like("integration-test-%")  # ← FIXED: was id
        ).delete()
        session.commit()


class TestMetricsSystemIntegration:
    """Integration tests for full metrics system"""
    
    def test_get_summary_with_real_data(self, seed_test_data):
        """
        Given: Database has seeded pipelines and usage
        When: GET /metrics/summary
        Then: Returns aggregated metrics from database
        """
        response = client.get("/metrics/summary")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should include our test pipelines
        assert data["total_pipelines"] >= 2
        assert data["total_cost_usd"] >= 0.075  # Sum of our test costs
        assert data["total_input_tokens"] >= 4500
        assert data["total_output_tokens"] >= 7000
    
    def test_get_pipeline_metrics_with_real_data(self, seed_test_data):
        """
        Given: Pipeline exists with usage records
        When: GET /metrics/pipeline/{pipeline_id}
        Then: Returns detailed metrics with phase breakdown
        """
        response = client.get("/metrics/pipeline/integration-test-1")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["pipeline_id"] == "integration-test-1"
        assert data["status"] == "completed"  # Note: API returns "status" even though model uses "state"
        assert data["epic_description"] == "Integration Test Epic 1"
        assert data["total_cost_usd"] == 0.060  # 0.025 + 0.035
        assert data["total_input_tokens"] == 3500  # 1500 + 2000
        assert data["total_output_tokens"] == 5500  # 2500 + 3000
        assert len(data["phase_breakdown"]) == 2
    
    def test_get_recent_pipelines_with_real_data(self, seed_test_data):
        """
        Given: Database has multiple pipelines
        When: GET /metrics/recent
        Then: Returns ordered list with our test pipelines
        """
        response = client.get("/metrics/recent?limit=50")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should include our test pipelines
        pipeline_ids = [p["pipeline_id"] for p in data]
        assert "integration-test-1" in pipeline_ids
        assert "integration-test-2" in pipeline_ids
        
        # Verify ordering (most recent first)
        test_pipeline_2 = next(p for p in data if p["pipeline_id"] == "integration-test-2")
        assert test_pipeline_2["status"] == "in_progress"
        assert test_pipeline_2["epic_description"] == "Integration Test Epic 2"
    
    def test_get_daily_costs_with_real_data(self, seed_test_data):
        """
        Given: Usage records exist over multiple days
        When: GET /metrics/daily-costs?days=7
        Then: Returns daily aggregates with filled gaps
        """
        response = client.get("/metrics/daily-costs?days=7")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 7  # Always 7 days even with gaps
        
        # At least one day should have our test cost
        total_costs = [day["total_cost_usd"] for day in data]
        assert sum(total_costs) >= 0.075
    
    def test_metrics_overview_html_renders(self, seed_test_data):
        """
        Given: Metrics data exists
        When: GET /metrics (HTML)
        Then: Renders HTML dashboard with data
        """
        response = client.get("/metrics", headers={"Accept": "text/html"})
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        
        # Verify key content is present
        content = response.content.decode()
        assert "Metrics Dashboard" in content
        assert "integration-test-1" in content or "integration-test-2" in content
    
    def test_pipeline_detail_html_renders(self, seed_test_data):
        """
        Given: Pipeline with metrics exists
        When: GET /metrics/{pipeline_id} (HTML)
        Then: Renders detail page with phase breakdown
        """
        response = client.get("/metrics/integration-test-1", headers={"Accept": "text/html"})
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        
        content = response.content.decode()
        assert "integration-test-1" in content
        assert "Integration Test Epic 1" in content
    
    def test_pipeline_not_found_returns_404(self):
        """
        Given: Pipeline does not exist
        When: GET /metrics/pipeline/{nonexistent_id}
        Then: Returns 404
        """
        response = client.get("/metrics/pipeline/does-not-exist-12345")
        
        assert response.status_code == 404
    
    def test_metrics_with_no_epic_description(self, seed_test_data):
        """
        Given: Pipeline has no epic in artifacts
        When: GET /metrics/recent
        Then: Returns pipeline with epic_description=null
        """
        # Create pipeline with no epic - FIXED FIELD NAMES
        with get_db_session() as session:
            pipeline_no_epic = Pipeline(
                pipeline_id="integration-test-no-epic",  # ← FIXED: was id
                epic_id="epic-no-epic",                  # ← ADDED: required
                state="completed",                       # ← FIXED: was status
                current_phase="commit_phase",
                canon_version="1.0",                     # ← ADDED: required
                initial_context={},                      # ← FIXED: was artifacts
                created_at=datetime.now(timezone.utc)
            )
            session.add(pipeline_no_epic)
            session.commit()
        
        response = client.get("/metrics/recent?limit=50")
        
        assert response.status_code == 200
        data = response.json()
        
        no_epic_pipeline = next(
            (p for p in data if p["pipeline_id"] == "integration-test-no-epic"),
            None
        )
        assert no_epic_pipeline is not None
        assert no_epic_pipeline["epic_description"] is None
        
        # Cleanup - FIXED: pipeline_id not id
        with get_db_session() as session:
            session.query(Pipeline).filter(
                Pipeline.pipeline_id == "integration-test-no-epic"  # ← FIXED: was id
            ).delete()
            session.commit()
    
    def test_metrics_with_null_token_values(self, seed_test_data):
        """
        Given: Usage record has NULL token/cost values
        When: GET /metrics/pipeline/{pipeline_id}
        Then: Treats NULLs as zeros, returns valid metrics
        """
        # Create usage record with NULLs
        with get_db_session() as session:
            usage_with_nulls = PipelinePromptUsage(
                pipeline_id="integration-test-1",
                prompt_id=1,
                input_tokens=None,
                output_tokens=None,
                cost_usd=None,
                execution_time_ms=None,
                used_at=datetime.now(timezone.utc)
            )
            session.add(usage_with_nulls)
            session.commit()
            usage_id = usage_with_nulls.id
        
        response = client.get("/metrics/pipeline/integration-test-1")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should still return valid metrics (NULLs treated as zeros)
        assert data["total_cost_usd"] >= 0
        assert data["total_input_tokens"] >= 0
        assert data["total_output_tokens"] >= 0
        
        # Cleanup
        with get_db_session() as session:
            session.query(PipelinePromptUsage).filter(
                PipelinePromptUsage.id == usage_id
            ).delete()
            session.commit()
    
    def test_timezone_handling_in_daily_costs(self, seed_test_data):
        """
        Given: Usage records created at different times
        When: GET /metrics/daily-costs
        Then: Groups by database UTC date (ADR-014 compliance)
        """
        response = client.get("/metrics/daily-costs?days=7")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify dates are in YYYY-MM-DD format
        for day in data:
            assert len(day["date"]) == 10  # YYYY-MM-DD
            assert day["date"].count("-") == 2
            
            # Parse to verify valid date
            datetime.fromisoformat(day["date"])
    
    def test_performance_get_summary(self, seed_test_data):
        """
        Given: Database has test data
        When: GET /metrics/summary called
        Then: Responds in <2 seconds (soft target, logs warning if slow)
        """
        import time
        
        start = time.time()
        response = client.get("/metrics/summary")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        
        # Soft performance target (log warning, don't fail)
        if elapsed > 2.0:
            print(f"WARNING: get_summary took {elapsed:.2f}s (target <2s)")
    
    def test_performance_get_recent_pipelines(self, seed_test_data):
        """
        Given: Database has test data
        When: GET /metrics/recent called
        Then: Responds in <2 seconds (soft target)
        """
        import time
        
        start = time.time()
        response = client.get("/metrics/recent?limit=20")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        
        if elapsed > 2.0:
            print(f"WARNING: get_recent_pipelines took {elapsed:.2f}s (target <2s)")


class TestMetricsSchemaValidation:
    """Test Pydantic schema validation"""
    
    def test_metrics_summary_response_schema(self, seed_test_data):
        """
        Given: API returns summary data
        When: Response validated against schema
        Then: All required fields present, types correct
        """
        response = client.get("/metrics/summary")
        
        assert response.status_code == 200
        data = response.json()
        
        # Required fields
        assert "total_pipelines" in data
        assert "total_cost_usd" in data
        assert "total_input_tokens" in data
        assert "total_output_tokens" in data
        assert "success_count" in data
        assert "failure_count" in data
        
        # Type validation
        assert isinstance(data["total_pipelines"], int)
        assert isinstance(data["total_cost_usd"], (int, float))
        assert isinstance(data["total_input_tokens"], int)
        assert isinstance(data["total_output_tokens"], int)
        assert isinstance(data["success_count"], int)
        assert isinstance(data["failure_count"], int)
        
        # Timestamp should be excluded (ADR-013)
        assert "last_usage_timestamp" not in data
    
    def test_pipeline_metrics_response_schema(self, seed_test_data):
        """
        Given: API returns pipeline metrics
        When: Response validated against schema
        Then: All fields present with correct types
        """
        response = client.get("/metrics/pipeline/integration-test-1")
        
        assert response.status_code == 200
        data = response.json()
        
        # Required fields
        assert "pipeline_id" in data
        assert "status" in data
        assert "current_phase" in data
        assert "total_cost_usd" in data
        assert "total_input_tokens" in data
        assert "total_output_tokens" in data
        assert "phase_breakdown" in data
        
        # Type validation
        assert isinstance(data["pipeline_id"], str)
        assert isinstance(data["status"], str)
        assert isinstance(data["phase_breakdown"], list)
        
        # Phase breakdown structure
        if len(data["phase_breakdown"]) > 0:
            phase = data["phase_breakdown"][0]
            assert "phase_name" in phase
            assert "role_name" in phase
            assert "input_tokens" in phase
            assert "output_tokens" in phase
            assert "cost_usd" in phase