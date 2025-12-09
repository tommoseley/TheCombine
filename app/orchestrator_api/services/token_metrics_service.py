"""TokenMetricsService - Business logic for token usage and cost metrics."""

import logging
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import text

from app.orchestrator_api.persistence.repositories.pipeline_prompt_usage_repository import (
    PipelinePromptUsageRepository,
)
from app.orchestrator_api.persistence.repositories.pipeline_repository import (
    PipelineRepository,
)
from app.orchestrator_api.persistence.database import get_db_session
from app.orchestrator_api.services.token_metrics_types import (
    MetricsSummary,
    PipelineMetrics,
    PipelineSummary,
    DailyCost,
    PhaseMetricsInternal,
)

logger = logging.getLogger(__name__)


class TokenMetricsService:
    """
    Service layer for token usage and cost metrics.

    Wraps all repository calls in try/except blocks.
    Returns safe defaults (zeros/empty/None) on errors.
    Never raises exceptions to router layer.
    """

    def __init__(self) -> None:
        """Initialize service (constructs repos internally)."""
        # No injected deps for MVP – repos constructed inside methods
        pass

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    def get_summary(self) -> MetricsSummary:
        """
        Get system-wide aggregated metrics.

        Returns:
            MetricsSummary with totals and counts.
            Returns zeros/None on error (never raises).
        """
        try:
            usage_repo = PipelinePromptUsageRepository()
            aggregates = usage_repo.get_system_aggregates()

            # Get success/failure counts
            with get_db_session() as session:
                success_count = (
                    session.execute(
                        text(
                            "SELECT COUNT(*) FROM pipelines "
                            "WHERE status = 'completed'"
                        )
                    ).scalar()
                    or 0
                )

                failure_count = (
                    session.execute(
                        text(
                            "SELECT COUNT(*) FROM pipelines "
                            "WHERE status IN ('failed', 'error')"
                        )
                    ).scalar()
                    or 0
                )

            return MetricsSummary(
                total_pipelines=aggregates["count"],
                total_cost_usd=aggregates["total_cost"] or 0.0,
                total_input_tokens=aggregates["total_input_tokens"] or 0,
                total_output_tokens=aggregates["total_output_tokens"] or 0,
                success_count=success_count,
                failure_count=failure_count,
                last_usage_timestamp=aggregates["last_timestamp"],
            )

        except Exception as e:
            logger.warning(
                f"Failed to get metrics summary: {type(e).__name__}: {e}"
            )
            return MetricsSummary(
                total_pipelines=0,
                total_cost_usd=0.0,
                total_input_tokens=0,
                total_output_tokens=0,
                success_count=0,
                failure_count=0,
                last_usage_timestamp=None,
            )

    # -------------------------------------------------------------------------
    # Per-pipeline
    # -------------------------------------------------------------------------
    def get_pipeline_metrics(
        self, pipeline_id: str
    ) -> Optional[PipelineMetrics]:
        """
        Get detailed metrics for a specific pipeline.

        Args:
            pipeline_id: Pipeline identifier

        Returns:
            PipelineMetrics with phase breakdown, or None if not found.
            Returns None on error (never raises).
        """
        try:
            pipeline_repo = PipelineRepository()
            pipeline = pipeline_repo.get_pipeline_with_epic(pipeline_id)

            if not pipeline:
                return None

            usage_repo = PipelinePromptUsageRepository()
            usage_records = usage_repo.get_pipeline_usage(pipeline_id)

            # Build phase breakdown
            phase_breakdown: list[PhaseMetricsInternal] = []
            total_input = 0
            total_output = 0
            total_cost = 0.0

            for record in usage_records:
                phase_breakdown.append(
                    PhaseMetricsInternal(
                        phase_name=record.phase_name,
                        role_name=record.role_name,
                        input_tokens=record.input_tokens or 0,
                        output_tokens=record.output_tokens or 0,
                        cost_usd=record.cost_usd or 0.0,
                        execution_time_ms=record.execution_time_ms,
                        timestamp=(
                            record.used_at.isoformat()
                            if getattr(record, "used_at", None)
                            else ""
                        ),
                    )
                )

                total_input += record.input_tokens or 0
                total_output += record.output_tokens or 0
                total_cost += record.cost_usd or 0.0

            return PipelineMetrics(
                pipeline_id=pipeline["pipeline_id"],
                status=pipeline["status"],
                current_phase=pipeline["current_phase"],
                epic_description=pipeline["epic_description"],
                total_cost_usd=total_cost,
                total_input_tokens=total_input,
                total_output_tokens=total_output,
                phase_breakdown=phase_breakdown,
            )

        except Exception as e:
            logger.warning(
                f"Failed to get pipeline metrics for {pipeline_id}: "
                f"{type(e).__name__}: {e}"
            )
            return None

    # -------------------------------------------------------------------------
    # Recent pipelines
    # -------------------------------------------------------------------------
    def get_recent_pipelines(
        self, limit: int = 20
    ) -> list[PipelineSummary]:
        """
        Get recent pipelines with aggregated usage.

        Args:
            limit: Maximum number of pipelines to return

        Returns:
            List of PipelineSummary objects.
            Returns empty list on error (never raises).
        """
        try:
            with get_db_session() as session:
                result = session.execute(
                    text(
                        """
                        SELECT 
                            p.id as pipeline_id,
                            p.status,
                            p.artifacts,
                            p.created_at,
                            COALESCE(u.total_cost, 0.0) as total_cost,
                            COALESCE(u.total_tokens, 0) as total_tokens
                        FROM pipelines p
                        LEFT JOIN (
                            SELECT 
                                pipeline_id,
                                SUM(cost_usd) as total_cost,
                                SUM(input_tokens + output_tokens) as total_tokens
                            FROM pipeline_prompt_usage
                            GROUP BY pipeline_id
                        ) u ON p.id = u.pipeline_id
                        ORDER BY p.created_at DESC
                        LIMIT :limit
                        """
                    ),
                    {"limit": limit},
                ).fetchall()

                pipelines: list[PipelineSummary] = []

                for row in result:
                    # Extract epic description defensively
                    epic_description = None
                    if row.artifacts:
                        try:
                            if isinstance(row.artifacts, str):
                                artifacts = json.loads(row.artifacts)
                            else:
                                artifacts = row.artifacts

                            if isinstance(artifacts, dict):
                                epic_description = (
                                    artifacts.get("epic", {}).get(
                                        "description"
                                    )
                                )
                                if not epic_description:
                                    epic_description = artifacts.get(
                                        "epic", {}
                                    ).get("epic_description")
                                if not epic_description:
                                    epic_description = artifacts.get(
                                        "pm", {}
                                    ).get("epic_description")
                        except (json.JSONDecodeError, AttributeError, TypeError):
                            # Leave epic_description as None
                            pass

                    pipelines.append(
                        PipelineSummary(
                            pipeline_id=row.pipeline_id,
                            epic_description=epic_description,
                            status=row.status,
                            total_cost_usd=float(row.total_cost),
                            total_tokens=int(row.total_tokens),
                            created_at=row.created_at,
                        )
                    )

                return pipelines

        except Exception as e:
            logger.warning(
                f"Failed to get recent pipelines: {type(e).__name__}: {e}"
            )
            return []

    # -------------------------------------------------------------------------
    # Daily costs
    # -------------------------------------------------------------------------
    def get_daily_costs(self, days: int = 7) -> list[DailyCost]:
        """
        Get daily cost aggregates for last N days.

        Fills missing dates with 0.0 cost.
        Uses database UTC timezone (see ADR-014).

        Args:
            days: Number of days to retrieve

        Returns:
            List of DailyCost objects for each day.
            Returns empty list on error (never raises).
        """
        try:
            usage_repo = PipelinePromptUsageRepository()
            aggregates = usage_repo.get_daily_aggregates(days=days)

            # Generate complete date range in UTC
            end_date = datetime.now(timezone.utc).date()
            start_date = end_date - timedelta(days=days - 1)

            all_dates = [
                (start_date + timedelta(days=i)).isoformat()
                for i in range(days)
            ]

            # Merge with actual data
            data_map = {row["date"]: row["total_cost"] for row in aggregates}

            return [
                DailyCost(date=date, total_cost_usd=data_map.get(date, 0.0))
                for date in all_dates
            ]

        except Exception as e:
            logger.warning(
                f"Failed to get daily costs: {type(e).__name__}: {e}"
            )
            return []