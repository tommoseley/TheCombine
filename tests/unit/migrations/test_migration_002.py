"""Tests for migration 002."""
import pytest
from sqlalchemy import create_engine, inspect, text
from app.orchestrator_api.persistence.migrations.migration_002_add_token_tracking import upgrade, downgrade
from app.orchestrator_api.persistence.database import Base

class TestMigration002:
    def test_upgrade_adds_columns(self, test_db_url):
        # Create base table first
        engine = create_engine(test_db_url)
        Base.metadata.create_all(engine)
        
        # Now run migration
        upgrade(test_db_url)
        
        inspector = inspect(engine)
        columns = [col["name"] for col in inspector.get_columns("pipeline_prompt_usage")]
        
        assert "input_tokens" in columns
        assert "output_tokens" in columns
        assert "cost_usd" in columns
        assert "model" in columns
        assert "execution_time_ms" in columns
    
    def test_upgrade_idempotent(self, test_db_url):
        # Create base table first
        engine = create_engine(test_db_url)
        Base.metadata.create_all(engine)
        
        # Run migration twice
        upgrade(test_db_url)
        upgrade(test_db_url)
        
        inspector = inspect(engine)
        columns = inspector.get_columns("pipeline_prompt_usage")
        assert len(columns) > 5
    
    def test_downgrade_removes_columns(self, test_db_url):
        # Create base table first
        engine = create_engine(test_db_url)
        Base.metadata.create_all(engine)
        
        # Run upgrade then downgrade
        upgrade(test_db_url)
        downgrade(test_db_url)
        
        inspector = inspect(engine)
        columns = [col["name"] for col in inspector.get_columns("pipeline_prompt_usage")]
        
        assert "input_tokens" not in columns
        assert "output_tokens" not in columns