"""Simple test to verify database state without repositories."""
import pytest
from sqlalchemy import text
from database import SessionLocal, engine


def test_simple_database_write_and_read(test_db):
    """Test that we can write and read from the same database."""
    from datetime import datetime, timezone
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Write directly
    with engine.begin() as conn:
        conn.execute(
            text("""INSERT INTO pipelines (pipeline_id, epic_id, state, current_phase, canon_version, created_at, updated_at)
                    VALUES (:pid, :eid, :state, :phase, :canon, :created, :updated)"""),
            {
                "pid": "test_123",
                "eid": "TEST",
                "state": "active",
                "phase": "pm_phase",
                "canon": "1.0",
                "created": now,
                "updated": now
            }
        )
    
    # Read with SessionLocal (what the repository uses)
    session = SessionLocal()
    try:
        from app.orchestrator_api.models.pipeline import Pipeline
        pipeline = session.query(Pipeline).filter(Pipeline.pipeline_id == "test_123").first()
        
        print(f"\n=== Test Result ===")
        if pipeline:
            print(f"SUCCESS: Found pipeline via SessionLocal(): {pipeline.pipeline_id}")
        else:
            print(f"FAILURE: Pipeline NOT found via SessionLocal()")
            
            # Try direct SQL
            with engine.connect() as conn:
                result = conn.execute(text("SELECT * FROM pipelines"))
                all_rows = result.fetchall()
                print(f"Direct SQL found {len(all_rows)} pipelines:")
                for row in all_rows:
                    print(f"  - {row}")
        
        assert pipeline is not None, "Pipeline should be found via SessionLocal()"
        assert pipeline.pipeline_id == "test_123"
        
    finally:
        session.close()