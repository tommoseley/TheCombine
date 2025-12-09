"""Test that exactly matches the original failing test structure."""
import pytest
from app.orchestrator_api.persistence.repositories.pipeline_prompt_usage_repository import PipelinePromptUsageRepository
from app.orchestrator_api.persistence.repositories.exceptions import RepositoryError


def test_record_usage_success(test_db, sample_pipeline, sample_role_prompt):
    """Test successful usage recording."""
    repo = PipelinePromptUsageRepository()
    
    result = repo.record_usage(
        pipeline_id=sample_pipeline.pipeline_id,
        role_name="pm",
        prompt_id=sample_role_prompt.id,
        phase_name="pm_phase"
    )
    
    assert result.id is not None
    assert result.pipeline_id == sample_pipeline.pipeline_id
    assert result.prompt_id == sample_role_prompt.id
    assert result.role_name == "pm"
    assert result.phase_name == "pm_phase"
    assert result.used_at is not None


def test_record_usage_invalid_pipeline_id(test_db, sample_role_prompt):
    """Test that invalid pipeline_id raises error."""
    repo = PipelinePromptUsageRepository()
    
    with pytest.raises(RepositoryError) as exc_info:
        repo.record_usage(
            pipeline_id="nonexistent_pipeline",
            role_name="pm",
            prompt_id=sample_role_prompt.id,
            phase_name="pm_phase"
        )
    
    assert "Pipeline not found" in str(exc_info.value) or "constraint" in str(exc_info.value).lower()


def test_record_usage_invalid_prompt_id(test_db, sample_pipeline):
    """Test that invalid prompt_id raises error."""
    repo = PipelinePromptUsageRepository()
    
    with pytest.raises(RepositoryError) as exc_info:
        repo.record_usage(
            pipeline_id=sample_pipeline.pipeline_id,
            role_name="pm",
            prompt_id="nonexistent_prompt",
            phase_name="pm_phase"
        )
    
    assert "Prompt not found" in str(exc_info.value) or "constraint" in str(exc_info.value).lower()


def test_get_by_pipeline(test_db, sample_pipeline, sample_role_prompt):
    """Test retrieving usage by pipeline."""
    repo = PipelinePromptUsageRepository()
    
    # Record some usage
    repo.record_usage(
        pipeline_id=sample_pipeline.pipeline_id,
        role_name="pm",
        prompt_id=sample_role_prompt.id,
        phase_name="pm_phase"
    )
    
    repo.record_usage(
        pipeline_id=sample_pipeline.pipeline_id,
        role_name="architect",
        prompt_id=sample_role_prompt.id,
        phase_name="arch_phase"
    )
    
    # Retrieve
    usages = repo.get_by_pipeline(sample_pipeline.pipeline_id)
    
    assert len(usages) == 2
    assert usages[0].role_name == "pm"
    assert usages[1].role_name == "architect"


def test_get_by_pipeline_empty(test_db, sample_pipeline):
    """Test retrieving usage for pipeline with no usage."""
    repo = PipelinePromptUsageRepository()
    
    usages = repo.get_by_pipeline(sample_pipeline.pipeline_id)
    
    assert len(usages) == 0


def test_get_by_prompt(test_db, sample_pipeline, sample_role_prompt):
    """Test retrieving usage by prompt."""
    repo = PipelinePromptUsageRepository()
    
    # Record usage
    repo.record_usage(
        pipeline_id=sample_pipeline.pipeline_id,
        role_name="pm",
        prompt_id=sample_role_prompt.id,
        phase_name="pm_phase"
    )
    
    # Retrieve
    usages = repo.get_by_prompt(sample_role_prompt.id)
    
    assert len(usages) == 1
    assert usages[0].pipeline_id == sample_pipeline.pipeline_id


def test_get_by_prompt_empty(test_db):
    """Test retrieving usage for prompt with no usage."""
    repo = PipelinePromptUsageRepository()
    
    usages = repo.get_by_prompt("nonexistent_prompt")
    
    assert len(usages) == 0