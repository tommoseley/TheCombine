"""Cost dashboard service.

Provides combined cost data from workflow telemetry and document builds.
Used by both the API and web routes.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.llm_logging import LLMRun
from app.llm import TelemetryService

logger = logging.getLogger(__name__)


async def get_cost_dashboard_data(
    db: AsyncSession,
    telemetry_service: TelemetryService,
    days: int = 7,
    source: Optional[str] = None,
) -> Dict[str, Any]:
    """Get cost dashboard data combining workflow and document costs.

    Args:
        db: Database session
        telemetry_service: Telemetry service for workflow costs
        days: Number of days to include (1-90)
        source: Optional filter - "workflows" or "documents"

    Returns:
        Dict with daily_data list and summary dict.
    """
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=days - 1)

    # Initialize daily data structure
    daily_totals = defaultdict(
        lambda: {
            "cost": 0.0,
            "tokens": 0,
            "calls": 0,
            "errors": 0,
            "workflow_cost": 0.0,
            "document_cost": 0.0,
        }
    )

    # Get workflow telemetry (unless filtered to documents only)
    if source != "documents":
        for i in range(days):
            day = today - timedelta(days=i)
            summary = await telemetry_service.get_daily_summary(day)
            day_str = day.strftime("%Y-%m-%d")
            daily_totals[day_str]["cost"] += float(summary.total_cost_usd)
            daily_totals[day_str]["workflow_cost"] += float(summary.total_cost_usd)
            daily_totals[day_str]["tokens"] += summary.input_tokens + summary.output_tokens
            daily_totals[day_str]["calls"] += summary.call_count
            daily_totals[day_str]["errors"] += summary.error_count

    # Get document build costs from llm_run table (unless filtered to workflows only)
    if source != "workflows":
        query = select(LLMRun).where(
            and_(
                LLMRun.artifact_type.isnot(None),
                LLMRun.started_at >= datetime.combine(start_date, datetime.min.time()),
            )
        )

        result = await db.execute(query)
        runs = result.scalars().all()

        for run in runs:
            if run.started_at:
                day_str = run.started_at.strftime("%Y-%m-%d")
                cost = float(run.cost_usd or 0)
                daily_totals[day_str]["cost"] += cost
                daily_totals[day_str]["document_cost"] += cost
                daily_totals[day_str]["tokens"] += (run.input_tokens or 0) + (
                    run.output_tokens or 0
                )
                daily_totals[day_str]["calls"] += 1
                if run.status == "FAILED":
                    daily_totals[day_str]["errors"] += 1

    from app.api.services.service_pure import aggregate_daily_costs

    daily_data, summary = aggregate_daily_costs(dict(daily_totals), today, days)

    return {
        "period_days": days,
        "source_filter": source,
        "daily_data": daily_data,
        "summary": summary,
    }
