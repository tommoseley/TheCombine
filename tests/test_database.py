"""
Test PostgreSQL database connection and basic operations.
"""
import pytest
from sqlalchemy import text
from database import engine, SessionLocal, Base


class TestDatabaseConnection:
    """Test database connectivity and basic operations."""
    
    def test_database_connection(self):
        """Verify PostgreSQL database is accessible."""
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            assert result.scalar() == 1
    
    def test_database_version(self):
        """Verify PostgreSQL version."""
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version()"))
            version = result.scalar()
            assert "PostgreSQL" in version
    
    def test_session_creation(self):
        """Verify SQLAlchemy session can be created."""
        session = SessionLocal()
        try:
            result = session.execute(text("SELECT 1"))
            assert result.scalar() == 1
        finally:
            session.close()
    
    def test_tables_exist(self):
        """Verify required tables exist in database."""
        required_tables = [
            'projects',
            'artifacts',
            'artifact_versions',
            'workflows',
            'files',
            'breadcrumb_files',
            'role_prompts'
        ]
        
        with engine.connect() as connection:
            for table in required_tables:
                result = connection.execute(text(
                    f"SELECT EXISTS (SELECT FROM information_schema.tables "
                    f"WHERE table_name = '{table}')"
                ))
                exists = result.scalar()
                assert exists, f"Table '{table}' does not exist"
    
    def test_timezone_handling(self):
        """Verify PostgreSQL returns timezone-aware timestamps."""
        with engine.connect() as connection:
            result = connection.execute(text("SELECT NOW()"))
            timestamp = result.scalar()
            # PostgreSQL TIMESTAMPTZ should return timezone-aware datetime
            assert timestamp.tzinfo is not None, "Timestamp should be timezone-aware"