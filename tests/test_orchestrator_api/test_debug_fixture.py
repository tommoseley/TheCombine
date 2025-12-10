"""Debug test to diagnose fixture visibility issue.

Run with: pytest tests/test_orchestrator_api/test_debug_fixture.py -v -s
"""
import pytest
from sqlalchemy import text
from database import SessionLocal, engine
from app.orchestrator_api.models.pipeline import Pipeline


def test_fixture_visibility_debug(test_db, sample_pipeline):
    """Debug test to see if fixture-created pipeline is visible."""
    print(f"\n{'='*60}")
    print(f"FIXTURE SAYS: pipeline_id = {sample_pipeline.pipeline_id}")
    print(f"{'='*60}")
    
    # Method 1: Check via ORM
    print("\n[Method 1: ORM Query]")
    session = SessionLocal()
    try:
        pipeline = session.query(Pipeline).filter(
            Pipeline.pipeline_id == sample_pipeline.pipeline_id
        ).first()
        
        if pipeline:
            print(f"✓ FOUND via ORM: {pipeline.pipeline_id}")
            print(f"  epic_id: {pipeline.epic_id}")
            print(f"  current_phase: {pipeline.current_phase}")
        else:
            print(f"✗ NOT FOUND via ORM")
            
        # List ALL pipelines
        all_pipelines = session.query(Pipeline).all()
        print(f"\nTotal pipelines in database: {len(all_pipelines)}")
        for p in all_pipelines:
            print(f"  - {p.pipeline_id} (epic: {p.epic_id})")
    finally:
        session.close()
    
    # Method 2: Check via raw SQL
    print("\n[Method 2: Raw SQL]")
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT pipeline_id, epic_id FROM pipelines WHERE pipeline_id = :pid"),
            {"pid": sample_pipeline.pipeline_id}
        )
        row = result.fetchone()
        if row:
            print(f"✓ FOUND via SQL: {row[0]}")
        else:
            print(f"✗ NOT FOUND via SQL")
        
        # List all via SQL
        result = conn.execute(text("SELECT pipeline_id, epic_id FROM pipelines"))
        rows = result.fetchall()
        print(f"\nTotal pipelines via SQL: {len(rows)}")
        for row in rows:
            print(f"  - {row[0]} (epic: {row[1]})")
    
    # Method 3: Check table structure
    print("\n[Method 3: Table Structure]")
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(pipelines)"))
        columns = result.fetchall()
        print("Columns in pipelines table:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
    
    print(f"\n{'='*60}")
    print("DEBUG TEST COMPLETE")
    print(f"{'='*60}\n")
    
    # This will pass - we're just debugging
    assert True