"""Tests for workflow endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestListWorkflows:
    """Tests for GET /api/v1/workflows."""
    
    def test_list_workflows_returns_workflows(self, client: TestClient):
        """List workflows returns available workflows."""
        response = client.get("/api/v1/workflows")
        
        assert response.status_code == 200
        data = response.json()
        assert "workflows" in data
        assert "total" in data
        assert data["total"] == 1
        assert len(data["workflows"]) == 1
    
    def test_list_workflows_summary_fields(self, client: TestClient):
        """Workflow summary contains expected fields."""
        response = client.get("/api/v1/workflows")
        
        data = response.json()
        workflow = data["workflows"][0]
        
        assert workflow["workflow_id"] == "test_workflow"
        assert workflow["name"] == "Test Workflow"
        assert workflow["description"] == "A test workflow for API testing"
        assert workflow["revision"] == "1"
        assert workflow["step_count"] == 2


class TestGetWorkflow:
    """Tests for GET /api/v1/workflows/{id}."""
    
    def test_get_workflow_found(self, client: TestClient):
        """Get workflow returns full details when found."""
        response = client.get("/api/v1/workflows/test_workflow")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["workflow_id"] == "test_workflow"
        assert data["name"] == "Test Workflow"
        assert data["schema_version"] == "workflow.v1"
    
    def test_get_workflow_has_scopes(self, client: TestClient):
        """Get workflow includes scope definitions."""
        response = client.get("/api/v1/workflows/test_workflow")
        data = response.json()
        
        assert "scopes" in data
        assert "project" in data["scopes"]
        assert "epic" in data["scopes"]
        assert data["scopes"]["project"]["parent"] is None
        assert data["scopes"]["epic"]["parent"] == "project"
    
    def test_get_workflow_has_document_types(self, client: TestClient):
        """Get workflow includes document type definitions."""
        response = client.get("/api/v1/workflows/test_workflow")
        data = response.json()
        
        assert "document_types" in data
        assert "discovery" in data["document_types"]
        assert "backlog" in data["document_types"]
        
        backlog = data["document_types"]["backlog"]
        assert backlog["acceptance_required"] is True
        assert backlog["accepted_by"] == ["PM"]
    
    def test_get_workflow_has_steps(self, client: TestClient):
        """Get workflow includes step summaries."""
        response = client.get("/api/v1/workflows/test_workflow")
        data = response.json()
        
        assert "steps" in data
        assert len(data["steps"]) == 2
        
        step = data["steps"][0]
        assert "step_id" in step
        assert "scope" in step
        assert "role" in step
        assert "produces" in step
    
    def test_get_workflow_not_found(self, client: TestClient):
        """Get workflow returns 404 for unknown workflow."""
        response = client.get("/api/v1/workflows/unknown_workflow")
        
        assert response.status_code == 404
        data = response.json()
        
        assert "detail" in data
        assert data["detail"]["error_code"] == "WORKFLOW_NOT_FOUND"
        assert "unknown_workflow" in data["detail"]["message"]


class TestGetStepSchema:
    """Tests for GET /api/v1/workflows/{id}/steps/{step}/schema."""
    
    def test_get_step_schema_found(self, client: TestClient):
        """Get step schema returns schema when found."""
        response = client.get("/api/v1/workflows/test_workflow/steps/discovery_step/schema")
        
        assert response.status_code == 200
        data = response.json()
        assert "type" in data
        assert data["type"] == "object"
    
    def test_get_step_schema_workflow_not_found(self, client: TestClient):
        """Get step schema returns 404 for unknown workflow."""
        response = client.get("/api/v1/workflows/unknown/steps/discovery_step/schema")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error_code"] == "WORKFLOW_NOT_FOUND"
    
    def test_get_step_schema_step_not_found(self, client: TestClient):
        """Get step schema returns 404 for unknown step."""
        response = client.get("/api/v1/workflows/test_workflow/steps/unknown_step/schema")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error_code"] == "STEP_NOT_FOUND"
