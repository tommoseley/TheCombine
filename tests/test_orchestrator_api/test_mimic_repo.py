"""Test that mimics the exact repository logic to find the issue."""
import pytest
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.orchestrator_api.persistence.database import SessionLocal, engine
from app.orchestrator_api.models.pipeline import Pipeline
from app.orchestrator_api.models.pipeline_prompt_usage import PipelinePromptUsage


def test_mimic_repository_logic(test_db, sample_pipeline, sample_role_prompt):
    """Mimic exact repository logic."""
    print(f"\n{'='*60}")
    print(f"Testing with pipeline: {sample_pipeline.pipeline_id}")
    print(f"Testing with prompt: {sample_role_prompt.id}")
    print(f"{'='*60}")
    
    # Verify pipeline exists
    print("\n[Step 1: Verify Pipeline Exists]")
    session = SessionLocal()
    try:
        pipeline = session.query(Pipeline).filter(
            Pipeline.pipeline_id == sample_pipeline.pipeline_id
        ).first()
        assert pipeline is not None, "Pipeline should exist!"
        print(f"✓ Pipeline exists: {pipeline.pipeline_id}")
    finally:
        session.close()
    
    # Verify prompt exists
    print("\n[Step 2: Verify Prompt Exists]")
    session = SessionLocal()
    try:
        from app.orchestrator_api.models.role_prompt import RolePrompt
        prompt = session.query(RolePrompt).filter(
            RolePrompt.id == sample_role_prompt.id
        ).first()
        assert prompt is not None, "Prompt should exist!"
        print(f"✓ Prompt exists: {prompt.id}")
    finally:
        session.close()
    
    # Now try to create usage record - EXACTLY as repository does
    print("\n[Step 3: Create Usage Record]")
    session = SessionLocal()
    try:
        # Create the usage record
        usage = PipelinePromptUsage(
            id=f"ppu_test123",
            pipeline_id=sample_pipeline.pipeline_id,
            prompt_id=sample_role_prompt.id,
            role_name="test_role",
            phase_name="test_phase",
            used_at=datetime.now(timezone.utc)
        )
        
        print(f"Created usage object: {usage.id}")
        print(f"  pipeline_id: {usage.pipeline_id}")
        print(f"  prompt_id: {usage.prompt_id}")
        
        # Add to session
        session.add(usage)
        print("✓ Added to session")
        
        # Commit
        session.commit()
        print("✓ Committed successfully!")
        
        # Verify it was saved
        saved = session.query(PipelinePromptUsage).filter(
            PipelinePromptUsage.id == "ppu_test123"
        ).first()
        assert saved is not None
        print(f"✓ Verified saved: {saved.id}")
        
    except IntegrityError as e:
        session.rollback()
        print(f"✗ IntegrityError: {e}")
        
        # Try to diagnose which FK failed
        print("\n[Diagnosis]")
        
        # Check pipeline FK
        p_check = session.query(Pipeline).filter(
            Pipeline.pipeline_id == sample_pipeline.pipeline_id
        ).first()
        print(f"Pipeline FK check: {'EXISTS' if p_check else 'MISSING'}")
        
        # Check prompt FK
        from app.orchestrator_api.models.role_prompt import RolePrompt
        pr_check = session.query(RolePrompt).filter(
            RolePrompt.id == sample_role_prompt.id
        ).first()
        print(f"Prompt FK check: {'EXISTS' if pr_check else 'MISSING'}")
        
        raise
    finally:
        session.close()
    
    print(f"\n{'='*60}")
    print("TEST PASSED - Usage record created successfully!")
    print(f"{'='*60}\n")