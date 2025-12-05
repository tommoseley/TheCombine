"""Debug test to verify database state."""
import pytest
from sqlalchemy import text
from app.orchestrator_api.persistence.database import SessionLocal, engine


def test_debug_database_state(test_db, sample_pipeline):
    """Debug test to check if pipeline exists."""
    from app.orchestrator_api.models.pipeline import Pipeline
    
    # Check with direct SQL
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM pipelines WHERE pipeline_id = 'pip_test_123'"))
        rows = result.fetchall()
        print(f"\n=== Direct SQL query ===")
        print(f"Found {len(rows)} rows")
        for row in rows:
            print(f"Row: {row}")
    
    # Check with ORM
    session = SessionLocal()
    try:
        pipeline = session.query(Pipeline).filter(Pipeline.pipeline_id == "pip_test_123").first()
        print(f"\n=== ORM query ===")
        if pipeline:
            print(f"Found pipeline: {pipeline.pipeline_id}")
        else:
            print(f"Pipeline NOT found via ORM")
            
        # List all pipelines
        all_pipelines = session.query(Pipeline).all()
        print(f"\n=== All pipelines ===")
        print(f"Total count: {len(all_pipelines)}")
        for p in all_pipelines:
            print(f"  - {p.pipeline_id}")
    finally:
        session.close()
    
    # The fixture should have returned a stub
    print(f"\n=== Fixture data ===")
    print(f"sample_pipeline.pipeline_id = {sample_pipeline.pipeline_id}")
    
    # Verify
    assert len(rows) == 1, "Pipeline should exist in database"