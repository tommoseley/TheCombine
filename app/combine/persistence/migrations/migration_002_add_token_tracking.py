"""Migration: Add token tracking columns to pipeline_prompt_usage."""
import logging

from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)


def upgrade(database_url: str):
    """Add token tracking columns."""
    engine = create_engine(database_url)

    with engine.connect() as conn:
        try:
            logger.info("Adding input_tokens column...")
            conn.execute(
                text(
                    "ALTER TABLE pipeline_prompt_usage "
                    "ADD COLUMN input_tokens INTEGER DEFAULT 0"
                )
            )
            conn.commit()
        except Exception as e:
            if "duplicate column" not in str(e).lower():
                raise
            logger.info("Column input_tokens already exists")

        try:
            logger.info("Adding output_tokens column...")
            conn.execute(
                text(
                    "ALTER TABLE pipeline_prompt_usage "
                    "ADD COLUMN output_tokens INTEGER DEFAULT 0"
                )
            )
            conn.commit()
        except Exception as e:
            if "duplicate column" not in str(e).lower():
                raise
            logger.info("Column output_tokens already exists")

        try:
            logger.info("Adding cost_usd column...")
            conn.execute(
                text(
                    "ALTER TABLE pipeline_prompt_usage "
                    "ADD COLUMN cost_usd DECIMAL(10, 6) DEFAULT 0.00"
                )
            )
            conn.commit()
        except Exception as e:
            if "duplicate column" not in str(e).lower():
                raise
            logger.info("Column cost_usd already exists")

        try:
            logger.info("Adding model column...")
            conn.execute(
                text(
                    "ALTER TABLE pipeline_prompt_usage "
                    "ADD COLUMN model VARCHAR(64) "
                    "DEFAULT 'claude-sonnet-4-20250514'"
                )
            )
            conn.commit()
        except Exception as e:
            if "duplicate column" not in str(e).lower():
                raise
            logger.info("Column model already exists")

        try:
            logger.info("Adding execution_time_ms column...")
            conn.execute(
                text(
                    "ALTER TABLE pipeline_prompt_usage "
                    "ADD COLUMN execution_time_ms INTEGER DEFAULT 0"
                )
            )
            conn.commit()
        except Exception as e:
            if "duplicate column" not in str(e).lower():
                raise
            logger.info("Column execution_time_ms already exists")

        try:
            logger.info("Creating index on pipeline_id and phase_name...")
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_usage_pipeline_phase "
                    "ON pipeline_prompt_usage(pipeline_id, phase_name)"
                )
            )
            conn.commit()
        except Exception as e:
            logger.warning(f"Index creation warning: {e}")

    logger.info("✅ Migration 002 complete")


def downgrade(database_url: str):
    """Remove token tracking columns."""
    engine = create_engine(database_url)

    with engine.connect() as conn:
        conn.execute(text("DROP INDEX IF EXISTS idx_usage_pipeline_phase"))
        conn.execute(text("ALTER TABLE pipeline_prompt_usage DROP COLUMN execution_time_ms"))
        conn.execute(text("ALTER TABLE pipeline_prompt_usage DROP COLUMN model"))
        conn.execute(text("ALTER TABLE pipeline_prompt_usage DROP COLUMN cost_usd"))
        conn.execute(text("ALTER TABLE pipeline_prompt_usage DROP COLUMN output_tokens"))
        conn.execute(text("ALTER TABLE pipeline_prompt_usage DROP COLUMN input_tokens"))
        conn.commit()

    logger.info("✅ Migration 002 rolled back")
