#!/usr/bin/env python3
"""
Database initialization script for The Combine.

Uses schema.sql for faithful reproduction of tables, indexes, 
functions, and triggers.
"""
import sys
import os
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text


def main():
    """Initialize database from schema.sql."""
    print("Initializing database...")
    
    # Get database URL from environment
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        return 1
    
    # Convert async URL to sync for this script
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    if "+psycopg2" not in sync_url:
        sync_url = sync_url.replace("postgresql://", "postgresql+psycopg2://")
    
    try:
        engine = create_engine(sync_url)
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Database connection successful")
        
        # Check if tables already exist
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'documents'
            """))
            tables_exist = result.scalar() > 0
        
        if tables_exist:
            print("✅ Tables already exist. Skipping schema creation.")
            return 0
        
        # Load and execute schema SQL
        schema_file = Path(__file__).parent / "schema.sql"
        if not schema_file.exists():
            print(f"⚠️ Schema file not found: {schema_file}")
            print("Falling back to SQLAlchemy model creation...")
            return create_tables_from_models(engine)
        
        print("📦 Creating schema from schema.sql...")
        sql_content = schema_file.read_text()
        
        # Clean up PostgreSQL-specific commands that cause issues
        lines = sql_content.split('\n')
        clean_lines = []
        skip_block = False
        
        for line in lines:
            stripped = line.strip()
            
            # Skip \restrict, \unrestrict commands
            if stripped.startswith('\\'):
                continue
            
            # Skip pg_catalog commands
            if 'pg_catalog.set_config' in line:
                continue
            
            # Skip OWNER TO statements (user might not exist)
            if 'OWNER TO' in stripped:
                continue
                
            # Skip ACL/privilege statements
            if any(x in stripped for x in [
                'ALTER DEFAULT PRIVILEGES',
                'GRANT ALL ON SCHEMA',
                'GRANT ALL ON TABLES',
                'GRANT ALL ON SEQUENCES'
            ]):
                continue
            
            clean_lines.append(line)
        
        clean_sql = '\n'.join(clean_lines)
        
        # Split into statements and execute one by one
        # This handles multi-statement SQL better
        with engine.connect() as conn:
            # First create extensions
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gin"))
                conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
                conn.commit()
                print("✅ Extensions created")
            except Exception as e:
                print(f"⚠️ Extension creation (may already exist): {e}")
                conn.rollback()
            
            # Execute the rest of the schema
            try:
                conn.execute(text(clean_sql))
                conn.commit()
            except Exception as e:
                print(f"⚠️ Schema execution issue: {e}")
                conn.rollback()
                # Try statement by statement
                return execute_statements_individually(engine, clean_sql)
        
        print("✅ Schema created successfully")
        verify_tables(engine)
        return 0
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


def execute_statements_individually(engine, sql_content):
    """Execute SQL statements one by one for better error handling."""
    print("Trying statement-by-statement execution...")
    
    # Very simple statement splitter (works for our schema)
    statements = []
    current = []
    in_function = False
    
    for line in sql_content.split('\n'):
        # Track if we're inside a function definition
        if 'CREATE FUNCTION' in line or 'CREATE OR REPLACE FUNCTION' in line:
            in_function = True
        
        current.append(line)
        
        # End of statement
        if line.strip().endswith(';') and not in_function:
            statements.append('\n'.join(current))
            current = []
        elif in_function and line.strip() == '$$;':
            in_function = False
            statements.append('\n'.join(current))
            current = []
    
    if current:
        statements.append('\n'.join(current))
    
    success = 0
    failed = 0
    
    with engine.connect() as conn:
        for stmt in statements:
            stmt = stmt.strip()
            if not stmt or stmt.startswith('--') or stmt.startswith('SET ') or stmt.startswith('SELECT '):
                continue
            
            try:
                conn.execute(text(stmt))
                conn.commit()
                success += 1
            except Exception as e:
                error_msg = str(e)
                # Ignore "already exists" errors
                if 'already exists' in error_msg:
                    continue
                # Show other errors but continue
                if len(stmt) > 100:
                    stmt_preview = stmt[:100] + "..."
                else:
                    stmt_preview = stmt
                print(f"⚠️ Skipped: {error_msg[:80]}")
                failed += 1
                conn.rollback()
    
    print(f"✅ Executed {success} statements ({failed} skipped)")
    verify_tables(engine)
    return 0


def verify_tables(engine):
    """Print list of created tables."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result]
        print(f"✅ Tables: {', '.join(tables)}")


def create_tables_from_models(engine):
    """Fallback: create tables from SQLAlchemy models."""
    try:
        from database import Base
        from app.api.models import (
            Project, Document, DocumentType, DocumentRelation,
            Role, RoleTask, RolePrompt, File
        )
        
        print("Creating tables from SQLAlchemy models...")
        Base.metadata.create_all(engine)
        print("✅ Tables created (note: custom functions/triggers not included)")
        return 0
    except Exception as e:
        print(f"❌ Model-based creation failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
