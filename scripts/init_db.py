#!/usr/bin/env python3
"""Database initialization script."""
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Now we can import
from sqlalchemy import create_engine, text
from config import Settings

def main():
    print("Initializing database...")
    
    try:
        settings = Settings()
    except Exception as e:
        print(f"Failed to load settings: {e}", file=sys.stderr)
        return 1
    
    if not create_tables(settings.DATABASE_URL):
        return 1
    
    if not run_migrations(settings.DATABASE_URL):
        return 1
    
    if not seed_data(settings.DATABASE_URL):
        return 1
    
    print("Database initialization complete")
    return 0

def create_tables(database_url: str) -> bool:
    print("Creating tables...")
    try:
        # Import after sys.path is set
        from database import Base
        
        engine = create_engine(database_url)
        Base.metadata.create_all(engine)
        print("Tables created")
        return True
    except Exception as e:
       print(f"Failed to create tables: {e}", file=sys.stderr)
       import traceback
       traceback.print_exc()
       return False

def run_migrations(database_url: str) -> bool:
    print("Running migrations...")
    try:
        # Import after sys.path is set
        from app.combine.persistence.migrations import migration_002_add_token_tracking
        
        migration_002_add_token_tracking.upgrade(database_url)
        print("Migrations complete")
        return True
    except Exception as e:
        print(f"Migration failed: {e}", file=sys.stderr)
        return False

def seed_data(database_url: str) -> bool:
    print("Seeding data...")
    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM role_prompts"))
            count = result.scalar()
            if count > 0:
                print("Data already seeded, skipping")
                return True
        
        # Import seed scripts after sys.path is set
        from scripts import seed_prompts, seed_phases
        seed_prompts.seed(database_url)
        seed_phases.seed(database_url)
        print("Data seeded")
        return True
    except Exception as e:
        print(f"Seeding failed: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    sys.exit(main())