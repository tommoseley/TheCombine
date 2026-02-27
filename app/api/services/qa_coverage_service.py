"""QA coverage service.

Provides QA coverage data extraction from workflow executions.
Used by both the API and web routes.
"""

import logging
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.workflow_execution import WorkflowExecution

logger = logging.getLogger(__name__)


async def get_qa_coverage(
    db: AsyncSession,
    execution_id: str,
) -> Optional[Dict[str, Any]]:
    """Get QA coverage data for a workflow execution.

    Args:
        db: Database session
        execution_id: Workflow execution ID

    Returns:
        Dict with execution info, constraint_lookup, qa_nodes, and summary.
        Returns None if execution not found.
    """
    # Get workflow execution
    result = await db.execute(
        select(WorkflowExecution).where(WorkflowExecution.execution_id == execution_id)
    )
    execution = result.scalar_one_or_none()

    if not execution:
        return None

    # Extract bound constraints from context_state for display
    context_state = execution.context_state or {}
    pgc_invariants = context_state.get("pgc_invariants", [])

    # Build lookup map: constraint_id -> constraint details
    constraint_lookup = {}
    for inv in pgc_invariants:
        cid = inv.get("id")
        if cid:
            constraint_lookup[cid] = {
                "id": cid,
                "question": inv.get("text", ""),
                "answer": inv.get("user_answer_label") or str(inv.get("user_answer", "")),
                "source": inv.get("binding_source", ""),
                "priority": inv.get("priority", ""),
            }

    # Extract QA node executions from execution_log
    execution_log = execution.execution_log or []
    qa_nodes = []

    for node_exec in execution_log:
        node_id = node_exec.get("node_id", "")
        # QA nodes typically have "qa" in their ID
        if "qa" in node_id.lower():
            qa_nodes.append(node_exec)

    # Process each QA node execution
    processed_qa_nodes = []
    summary = {
        "total_checks": 0,
        "passed": 0,
        "failed": 0,
        "total_errors": 0,
        "total_warnings": 0,
        "total_constraints": 0,
        "satisfied": 0,
        "missing": 0,
        "contradicted": 0,
        "reopened": 0,
        "not_evaluated": 0,
    }

    for qa_node in qa_nodes:
        node_id = qa_node.get("node_id")
        outcome = qa_node.get("outcome")
        timestamp = qa_node.get("timestamp")
        metadata = qa_node.get("metadata", {})

        summary["total_checks"] += 1
        if outcome == "success":
            summary["passed"] += 1
        else:
            summary["failed"] += 1

        # Extract semantic QA report if present
        semantic_report = metadata.get("semantic_qa_report")
        coverage_items = []
        findings = []
        report_summary = None

        if semantic_report:
            report_summary = semantic_report.get("summary", {})
            summary["total_errors"] += report_summary.get("errors", 0)
            summary["total_warnings"] += report_summary.get("warnings", 0)

            coverage = semantic_report.get("coverage", {})
            coverage_items = coverage.get("items", [])

            # Count per-constraint statuses
            for item in coverage_items:
                status = item.get("status", "not_evaluated")
                summary["total_constraints"] += 1
                if status == "satisfied":
                    summary["satisfied"] += 1
                elif status == "missing":
                    summary["missing"] += 1
                elif status == "contradicted":
                    summary["contradicted"] += 1
                elif status == "reopened":
                    summary["reopened"] += 1
                else:
                    summary["not_evaluated"] += 1

            findings = semantic_report.get("findings", [])

        # Extract Layer 1 drift issues
        drift_errors = metadata.get("drift_errors", [])
        drift_warnings = metadata.get("drift_warnings", [])

        # Extract code validation issues
        code_validation_warnings = metadata.get("code_validation_warnings", [])
        code_validation_errors = metadata.get("validation_errors", [])

        processed_qa_nodes.append({
            "node_id": node_id,
            "outcome": outcome,
            "timestamp": timestamp,
            "qa_passed": metadata.get("qa_passed", outcome == "success"),
            "validation_source": metadata.get("validation_source"),
            "semantic_report": semantic_report,
            "report_summary": report_summary,
            "coverage_items": coverage_items,
            "findings": findings,
            "drift_errors": drift_errors,
            "drift_warnings": drift_warnings,
            "code_validation_warnings": code_validation_warnings,
            "code_validation_errors": code_validation_errors,
        })

    return {
        "execution_id": execution_id,
        "workflow_id": execution.workflow_id,
        "document_type": execution.document_type,
        "constraint_lookup": constraint_lookup,
        "qa_nodes": processed_qa_nodes,
        "summary": summary,
    }
