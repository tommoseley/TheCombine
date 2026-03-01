"""Pure data transformation functions for various service modules.

Extracted per WS-CRAP-003 from:
- qa_coverage_service.py
- dashboard_service.py
- cost_service.py
- transcript_service.py
- mechanical_ops_service.py

All functions are pure (no DB, no I/O, no logging) to enable Tier-1 testing.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo


# =========================================================================
# QA Coverage (from qa_coverage_service.py)
# =========================================================================


def build_constraint_lookup(
    pgc_invariants: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Build a constraint lookup map from PGC invariants.

    Args:
        pgc_invariants: List of PGC invariant dicts from context_state

    Returns:
        Dict mapping constraint_id -> constraint detail dict
    """
    lookup = {}
    for inv in pgc_invariants:
        cid = inv.get("id")
        if cid:
            lookup[cid] = {
                "id": cid,
                "question": inv.get("text", ""),
                "answer": inv.get("user_answer_label") or str(inv.get("user_answer", "")),
                "source": inv.get("binding_source", ""),
                "priority": inv.get("priority", ""),
            }
    return lookup


def process_qa_nodes(
    execution_log: List[Dict[str, Any]],
) -> tuple:
    """Process execution log entries to extract and summarize QA nodes.

    Args:
        execution_log: List of node execution log entries

    Returns:
        Tuple of (processed_qa_nodes_list, summary_dict)
    """
    qa_nodes = [
        entry for entry in execution_log
        if "qa" in entry.get("node_id", "").lower()
    ]

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

    processed = []
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

        drift_errors = metadata.get("drift_errors", [])
        drift_warnings = metadata.get("drift_warnings", [])
        code_validation_warnings = metadata.get("code_validation_warnings", [])
        code_validation_errors = metadata.get("validation_errors", [])

        processed.append({
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

    return processed, summary


# =========================================================================
# Dashboard (from dashboard_service.py)
# =========================================================================


def sort_key_datetime(x: Dict[str, Any]) -> datetime:
    """Sort key that handles mixed timezone-aware/naive datetimes.

    Args:
        x: Dict with optional 'started_at' key

    Returns:
        Timezone-aware datetime for sorting
    """
    dt = x.get("started_at")
    if dt is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def format_execution_dates(
    executions: List[Dict[str, Any]],
    display_tz: ZoneInfo,
) -> List[Dict[str, Any]]:
    """Format started_at dates for display in executions list.

    Mutates the execution dicts in-place, adding started_at_formatted
    and started_at_iso fields.

    Args:
        executions: List of execution dicts with 'started_at' key
        display_tz: Timezone for formatting

    Returns:
        The same list (modified in-place)
    """
    for e in executions:
        if e["started_at"]:
            dt = e["started_at"]
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            local_dt = dt.astimezone(display_tz)
            e["started_at_formatted"] = local_dt.strftime("%Y-%m-%d %H:%M")
            e["started_at_iso"] = dt.isoformat()
        else:
            e["started_at_formatted"] = None
            e["started_at_iso"] = None
    return executions


def compute_dashboard_stats(
    workflow_count: int,
    running_count: int,
    waiting_count: int,
    doc_builds_today: int,
) -> Dict[str, Any]:
    """Compute dashboard stats dict.

    Args:
        workflow_count: Total number of workflows
        running_count: Number of running executions
        waiting_count: Number of executions waiting for action
        doc_builds_today: Number of document builds today

    Returns:
        Stats dict
    """
    return {
        "total_workflows": workflow_count,
        "running_executions": running_count,
        "waiting_action": waiting_count,
        "doc_builds_today": doc_builds_today,
    }


# =========================================================================
# Cost (from cost_service.py)
# =========================================================================


def aggregate_daily_costs(
    daily_totals: Dict[str, Dict[str, Any]],
    today: date,
    days: int,
) -> tuple:
    """Build daily_data list and compute summary from daily totals.

    Args:
        daily_totals: Dict mapping date_str -> cost/token/call/error totals
        today: Today's date
        days: Number of days in the period

    Returns:
        Tuple of (daily_data_list, summary_dict)
    """
    daily_data = []
    total_cost = 0.0
    total_tokens = 0
    total_calls = 0
    total_errors = 0

    for i in range(days - 1, -1, -1):
        day = today - timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        data = daily_totals.get(day_str, {
            "cost": 0.0,
            "tokens": 0,
            "calls": 0,
            "errors": 0,
            "workflow_cost": 0.0,
            "document_cost": 0.0,
        })

        daily_data.append({
            "date": day_str,
            "date_short": day.strftime("%m/%d"),
            "cost": data["cost"],
            "tokens": data["tokens"],
            "calls": data["calls"],
            "errors": data["errors"],
            "workflow_cost": data["workflow_cost"],
            "document_cost": data["document_cost"],
        })

        total_cost += data["cost"]
        total_tokens += data["tokens"]
        total_calls += data["calls"]
        total_errors += data["errors"]

    avg_cost_per_day = total_cost / days if days > 0 else 0
    avg_cost_per_call = total_cost / total_calls if total_calls > 0 else 0
    success_rate = (1 - (total_errors / total_calls)) * 100 if total_calls > 0 else 100

    summary = {
        "total_cost": round(total_cost, 4),
        "total_tokens": total_tokens,
        "total_calls": total_calls,
        "total_errors": total_errors,
        "avg_cost_per_day": round(avg_cost_per_day, 4),
        "avg_cost_per_call": round(avg_cost_per_call, 6),
        "success_rate": round(success_rate, 1),
    }

    return daily_data, summary


# =========================================================================
# Transcript (from transcript_service.py)
# =========================================================================


def build_transcript_entry(
    run_number: int,
    run_id: str,
    role: Optional[str],
    prompt_id: Optional[str],
    node_id: Optional[str],
    prompt_sources: Optional[Any],
    model_name: Optional[str],
    status: Optional[str],
    started_at: Optional[datetime],
    ended_at: Optional[datetime],
    total_tokens: Optional[int],
    cost_usd: Optional[Any],
    inputs: List[Dict[str, Any]],
    outputs: List[Dict[str, Any]],
    display_tz: ZoneInfo,
) -> Dict[str, Any]:
    """Build a single transcript entry dict from run data.

    Pure transformation: no DB, no I/O.

    Args:
        run_number: Sequential run number
        run_id: Full run UUID as string
        role: Role name
        prompt_id: Prompt/task reference
        node_id: Workflow node ID (from metadata)
        prompt_sources: Prompt sources (from metadata)
        model_name: LLM model name
        status: Run status
        started_at: Start timestamp
        ended_at: End timestamp
        total_tokens: Total token count
        cost_usd: Cost in USD (Decimal or float)
        inputs: Resolved input dicts
        outputs: Resolved output dicts
        display_tz: Timezone for display formatting

    Returns:
        Transcript entry dict
    """
    duration_seconds = None
    duration_str = None
    if started_at and ended_at:
        duration_seconds = (ended_at - started_at).total_seconds()
        duration_str = f"{duration_seconds:.1f}s"

    started_at_time = None
    started_at_iso = None
    if started_at:
        started_at_time = started_at.astimezone(display_tz).strftime("%H:%M:%S")
        started_at_iso = started_at.isoformat()

    return {
        "run_number": run_number,
        "run_id": run_id,
        "run_id_short": run_id[:8],
        "role": role,
        "task_ref": prompt_id,
        "node_id": node_id,
        "prompt_sources": prompt_sources,
        "model": model_name,
        "status": status,
        "started_at_time": started_at_time,
        "started_at_iso": started_at_iso,
        "duration": duration_str,
        "duration_seconds": duration_seconds,
        "tokens": total_tokens,
        "cost": float(cost_usd) if cost_usd else None,
        "inputs": inputs,
        "outputs": outputs,
    }


def compute_transcript_totals(
    entries: List[Dict[str, Any]],
) -> tuple:
    """Compute total tokens and cost from transcript entries.

    Args:
        entries: List of transcript entry dicts

    Returns:
        Tuple of (total_tokens, total_cost)
    """
    total_tokens = 0
    total_cost = 0.0
    for entry in entries:
        if entry["tokens"]:
            total_tokens += entry["tokens"]
        if entry["cost"]:
            total_cost += entry["cost"]
    return total_tokens, total_cost


def format_transcript_timestamps(
    started_at: Optional[datetime],
    ended_at: Optional[datetime],
    display_tz: ZoneInfo,
) -> Dict[str, Optional[str]]:
    """Format execution start/end timestamps for transcript header.

    Args:
        started_at: First run start time
        ended_at: Last run end time
        display_tz: Timezone for formatting

    Returns:
        Dict with started_at_formatted, started_at_iso,
        ended_at_formatted, ended_at_iso
    """
    result: Dict[str, Optional[str]] = {
        "started_at_formatted": None,
        "started_at_iso": None,
        "ended_at_formatted": None,
        "ended_at_iso": None,
    }

    if started_at:
        result["started_at_formatted"] = started_at.astimezone(display_tz).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        result["started_at_iso"] = started_at.isoformat()

    if ended_at:
        result["ended_at_formatted"] = ended_at.astimezone(display_tz).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        result["ended_at_iso"] = ended_at.isoformat()

    return result


# =========================================================================
# Mechanical Ops (from mechanical_ops_service.py)
# =========================================================================


def build_operation_summary(
    op_id: str,
    op_name: str,
    op_description: str,
    op_type: str,
    op_metadata: Dict[str, Any],
    type_name: Optional[str],
    type_category: Optional[str],
    active_version: str,
) -> Dict[str, Any]:
    """Build a mechanical operation summary dict.

    Args:
        op_id: Operation identifier
        op_name: Operation name
        op_description: Operation description
        op_type: Operation type ID
        op_metadata: Operation metadata dict
        type_name: Resolved type name (None if type not found)
        type_category: Resolved type category (None if type not found)
        active_version: Active version string

    Returns:
        Operation summary dict
    """
    return {
        "op_id": op_id,
        "name": op_name,
        "description": op_description,
        "type": op_type,
        "type_name": type_name or op_type,
        "category": type_category or "uncategorized",
        "active_version": active_version,
        "tags": op_metadata.get("tags", []),
    }
