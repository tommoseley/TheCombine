#!/usr/bin/env python3
"""
Seed database with initial data for The Combine.

Loads document_types, roles, and role_tasks.
Idempotent - checks if data exists before inserting.
"""
import sys
import os
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text


def main():
    """Seed database with initial data."""
    print("Seeding database...")
    
    # Get database URL from environment
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        return 1
    
    # Convert async URL to sync for this script
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    sync_url = sync_url.replace("postgresql://", "postgresql+psycopg2://")
    
    try:
        engine = create_engine(sync_url)
        
        with engine.connect() as conn:
            # Check if already seeded
            result = conn.execute(text("SELECT COUNT(*) FROM document_types"))
            count = result.scalar()
            
            if count > 0:
                print(f"✅ Database already seeded ({count} document types). Skipping.")
                return 0
            
            print("Inserting seed data...")
            
            # Load and execute seed SQL
            seed_file = Path(__file__).parent / "seed_data.sql"
            if not seed_file.exists():
                print(f"❌ Seed file not found: {seed_file}")
                return 1
            
            sql_content = seed_file.read_text()
            
            # Remove PostgreSQL-specific commands that psycopg2 doesn't understand
            lines = sql_content.split('\n')
            clean_lines = []
            for line in lines:
                # Skip \restrict, \unrestrict, and other backslash commands
                if line.strip().startswith('\\'):
                    continue
                # Skip SET commands that might cause issues
                if line.strip().startswith('SELECT pg_catalog.'):
                    continue
                clean_lines.append(line)
            
            clean_sql = '\n'.join(clean_lines)
            
            # Split into individual statements and execute
            # Simple split on semicolon - works for INSERT statements
            statements = clean_sql.split(';')
            
            inserted_counts = {
                'document_types': 0,
                'roles': 0,
                'role_tasks': 0
            }
            
            for stmt in statements:
                stmt = stmt.strip()
                if not stmt:
                    continue
                if stmt.startswith('--'):
                    continue
                if stmt.startswith('INSERT INTO'):
                    try:
                        conn.execute(text(stmt))
                        # Track what we inserted
                        if 'document_types' in stmt:
                            inserted_counts['document_types'] += 1
                        elif 'role_tasks' in stmt:
                            inserted_counts['role_tasks'] += 1
                        elif 'roles' in stmt:
                            inserted_counts['roles'] += 1
                    except Exception as e:
                        print(f"⚠️ Statement failed: {str(e)[:100]}")
                        continue
            
            conn.commit()
            
            print(f"✅ Inserted {inserted_counts['document_types']} document types")
            print(f"✅ Inserted {inserted_counts['roles']} roles")
            print(f"✅ Inserted {inserted_counts['role_tasks']} role tasks")
            print("✅ Database seeding complete")
            return 0
        
    except Exception as e:
        print(f"❌ Database seeding failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
