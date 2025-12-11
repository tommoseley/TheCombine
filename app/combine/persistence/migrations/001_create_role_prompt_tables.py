"""
Migration: Create role prompt and phase configuration tables.

Part of PIPELINE-175A: Data-Described Pipeline Infrastructure.

Creates:
- role_prompts
- phase_configurations
- pipeline_prompt_usage

Run: python -m app.orchestrator_api.persistence.migrations.001_create_role_prompt_tables
"""
from sqlalchemy import create_engine, inspect
from database import Base
from app.combine.models.role_prompt import RolePrompt
from app.combine.models.phase_configuration import PhaseConfiguration
from app.combine.models.pipeline_prompt_usage import PipelinePromptUsage
from config import settings


def upgrade():
    """Create tables."""
    engine = create_engine(settings.DATABASE_URL)
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    tables_to_create = []
    
    # Check which tables need to be created
    if "role_prompts" not in existing_tables:
        tables_to_create.append(Base.metadata.tables["role_prompts"])
    
    if "phase_configurations" not in existing_tables:
        tables_to_create.append(Base.metadata.tables["phase_configurations"])
    
    if "pipeline_prompt_usage" not in existing_tables:
        tables_to_create.append(Base.metadata.tables["pipeline_prompt_usage"])
    
    # Create only missing tables (idempotent)
    if tables_to_create:
        Base.metadata.create_all(engine, tables=tables_to_create)
        for table in tables_to_create:
            print(f"✓ Created {table.name} table")
    else:
        print("✓ All tables already exist, skipping creation")


def downgrade():
    """Drop tables."""
    engine = create_engine(settings.DATABASE_URL)
    
    # Drop in reverse order (foreign key dependencies)
    Base.metadata.drop_all(engine, tables=[
        Base.metadata.tables["pipeline_prompt_usage"],
        Base.metadata.tables["phase_configurations"],
        Base.metadata.tables["role_prompts"],
    ])
    
    print("✓ Dropped pipeline_prompt_usage table")
    print("✓ Dropped phase_configurations table")
    print("✓ Dropped role_prompts table")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()