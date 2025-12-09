"""Test that calls the actual repository to see the real error."""
import pytest
from app.orchestrator_api.persistence.repositories.pipeline_prompt_usage_repository import PipelinePromptUsageRepository
from app.orchestrator_api.persistence.repositories.exceptions import RepositoryError


def test_actual_repository_call(test_db, sample_pipeline, sample_role_prompt):
    """Call the actual repository."""
    print(f"\n{'='*60}")
    print(f"Calling actual repository")
    print(f"Pipeline: {sample_pipeline.pipeline_id}")
    print(f"Prompt: {sample_role_prompt.id}")
    print(f"{'='*60}\n")
    
    repo = PipelinePromptUsageRepository()
    
    try:
        result = repo.record_usage(
            pipeline_id=sample_pipeline.pipeline_id,
            role_name="test_role",
            prompt_id=sample_role_prompt.id,
            phase_name="test_phase"
        )
        print(f"✓ SUCCESS!")
        print(f"  Usage ID: {result.id}")
        print(f"  Pipeline ID: {result.pipeline_id}")
        print(f"  Prompt ID: {result.prompt_id}")
        print(f"  Role: {result.role_name}")
        print(f"  Phase: {result.phase_name}")
        
    except RepositoryError as e:
        print(f"✗ RepositoryError: {e}")
        print(f"  Error type: {type(e)}")
        
        # Print the underlying exception if available
        if hasattr(e, '__cause__'):
            print(f"  Caused by: {e.__cause__}")
            print(f"  Cause type: {type(e.__cause__)}")
        
        raise
    
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        print(f"  Error type: {type(e)}")
        raise
    
    print(f"\n{'='*60}")
    print("TEST COMPLETE")
    print(f"{'='*60}\n")