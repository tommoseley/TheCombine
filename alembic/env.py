"""
Alembic environment configuration for The Combine.

Configured to:
- Use DATABASE_URL from config/settings
- Import all models for autogenerate support
- Support both online and offline migrations
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# =============================================================================
# COMBINE-SPECIFIC CONFIGURATION
# =============================================================================

# Import your settings to get DATABASE_URL
from config import settings

# Import Base and all models for autogenerate support
from database import Base

# Import all models here so they're registered with Base.metadata
# This enables autogenerate to detect changes
from app.api.models.artifact import Artifact
from app.api.models.project import Project
from app.api.models.role_prompt import RolePrompt  # If this exists
# from app.combine.models.role import Role  # Uncomment if exists
# from app.combine.models.role_task import RoleTask  # Uncomment if exists
from app.api.models.document_type import DocumentType  # NEW - add after creating

# =============================================================================
# ALEMBIC CONFIGURATION
# =============================================================================

# This is the Alembic Config object
config = context.config

# Override sqlalchemy.url with our settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    
    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the
    Engine creation we don't even need a DBAPI to be available.
    
    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    
    In this scenario we need to create an Engine and associate
    a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()