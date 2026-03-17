"""
Admin API routes for The Combine.

ADR-010 Week 3: LLM execution replay functionality.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID, uuid4
from typing import Dict, Any, Optional
from pydantic import BaseModel
import hashlib
import logging

from app.core.database import get_db
from app.domain.repositories.postgres_llm_log_repository import PostgresLLMLogRepository
from app.domain.services.llm_execution_logger import LLMExecutionLogger
from anthropic import Anthropic
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ================================================================================
# Response Models
# ===============================================================================

class ReplayComparison(BaseModel):
    """Comparison between original and replay runs."""
    original_run_id: str
    replay_run_id: str
    metadata: Dict[str, Any]
    token_delta: Dict[str, int]
    cost_delta_usd: Optional[float]
    outputs: Dict[str, Any]
    notes: list[str]


class ReplayResponse(BaseModel):
    """Response from replay endpoint."""
    status: str
    original_run_id: str
    replay_run_id: str
    comparison: ReplayComparison


class ReplayOverridesRequest(BaseModel):
    """Optional overrides for replay experiments (WS-PI-0B)."""
    system_prompt_override: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class LLMRunSummary(BaseModel):
    """Summary of an LLM run for query results."""
    id: str
    artifact_type: Optional[str]
    prompt_id: str
    prompt_version: str
    status: str
    project_id: Optional[str]
    started_at: Optional[str]
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    total_tokens: Optional[int]


class LLMRunQueryResponse(BaseModel):
    """Response from LLM run query endpoint."""
    runs: list[LLMRunSummary]
    total: int
    limit: int
    offset: int


# ================================================================================
# Helper Functions
# ===============================================================================

async def reconstruct_inputs(db: AsyncSession, run_id: UUID) -> Dict[str, str]:
    """
    Reconstruct inputs from llm_run_input_ref and llm_content tables via ORM.
    
    Returns dict mapping input kind -> content text.
    """
    from sqlalchemy import select
    from app.api.models.llm_log import LLMRunInputRef, LLMContent
    
    # Join input refs with content
    result = await db.execute(
        select(LLMRunInputRef.kind, LLMContent.content_text)
        .join(LLMContent, LLMRunInputRef.content_hash == LLMContent.content_hash)
        .where(LLMRunInputRef.llm_run_id == run_id)
        .order_by(LLMRunInputRef.created_at)
    )
    rows = result.all()
    
    if not rows:
        raise ValueError(f"No inputs found for run {run_id}")
    
    inputs = {}
    for row in rows:
        kind = row.kind
        content = row.content_text
        
        if kind in inputs:
            inputs[kind] = inputs[kind] + "\n---\n" + content
        else:
            inputs[kind] = content
    
    logger.info(f"[ADR-010] Reconstructed {len(inputs)} input kinds for run {run_id}")
    return inputs


async def get_original_run(db: AsyncSession, run_id: UUID) -> Dict[str, Any]:
    """Load original run record via ORM."""
    from sqlalchemy import select
    from app.api.models.llm_log import LLMRun
    
    result = await db.execute(
        select(LLMRun).where(LLMRun.id == run_id)
    )
    row = result.scalar_one_or_none()
    
    if not row:
        raise ValueError(f"Run {run_id} not found")
    
    return {
        "id": row.id,
        "correlation_id": row.correlation_id,
        "project_id": row.project_id,
        "artifact_type": row.artifact_type,
        "role": row.role,
        "model_provider": row.model_provider,
        "model_name": row.model_name,
        "prompt_id": row.prompt_id,
        "prompt_version": row.prompt_version,
        "effective_prompt_hash": row.effective_prompt_hash,
        "status": row.status,
        "started_at": row.started_at,
        "ended_at": row.ended_at,
        "input_tokens": row.input_tokens,
        "output_tokens": row.output_tokens,
        "total_tokens": row.total_tokens,
        "cost_usd": row.cost_usd,
        "metadata": row.metadata or {},
    }


async def get_run_output(db: AsyncSession, run_id: UUID) -> Optional[str]:
    """Get the raw output text for a run via ORM."""
    from sqlalchemy import select, and_
    from app.api.models.llm_log import LLMRunOutputRef, LLMContent
    
    result = await db.execute(
        select(LLMContent.content_text)
        .join(LLMRunOutputRef, LLMRunOutputRef.content_hash == LLMContent.content_hash)
        .where(
            and_(
                LLMRunOutputRef.llm_run_id == run_id,
                LLMRunOutputRef.kind == 'raw_text'
            )
        )
        .limit(1)
    )
    row = result.first()
    
    return row[0] if row else None

def compare_runs(
    original: Dict[str, Any],
    replay: Dict[str, Any],
    original_output: Optional[str],
    replay_output: Optional[str],
) -> ReplayComparison:
    """
    Compare original and replay runs.
    
    Returns structured comparison with deltas and notes.
    """
    notes = []
    
    # Token delta
    orig_input = original.get("input_tokens") or 0
    orig_output = original.get("output_tokens") or 0
    replay_input = replay.get("input_tokens") or 0
    replay_output_tokens = replay.get("output_tokens") or 0
    
    token_delta = {
        "input_tokens": replay_input - orig_input,
        "output_tokens": replay_output_tokens - orig_output,
        "total_tokens": (replay_input + replay_output_tokens) - (orig_input + orig_output),
    }
    
    if token_delta["input_tokens"] == 0:
        notes.append("Input token count identical (prompt unchanged)")
    else:
        notes.append(f"Input tokens differ by {token_delta['input_tokens']}")
    
    # Cost delta
    orig_cost = float(original.get("cost_usd") or 0)
    replay_cost = float(replay.get("cost_usd") or 0)
    cost_delta = replay_cost - orig_cost if (orig_cost or replay_cost) else None
    
    # Output comparison
    output_comparison = {}
    if original_output and replay_output:
        orig_hash = hashlib.sha256(original_output.encode()).hexdigest()[:16]
        replay_hash = hashlib.sha256(replay_output.encode()).hexdigest()[:16]
        identical = original_output == replay_output
        
        output_comparison = {
            "original_hash": f"sha256:{orig_hash}",
            "replay_hash": f"sha256:{replay_hash}",
            "identical": identical,
            "original_length": len(original_output),
            "replay_length": len(replay_output),
            "length_delta": len(replay_output) - len(original_output),
        }
        
        if identical:
            notes.append("Output content identical (rare for LLM)")
        else:
            notes.append("Output content differs (expected - LLM is stochastic)")
    else:
        output_comparison = {
            "original_hash": None,
            "replay_hash": None,
            "identical": False,
            "note": "One or both outputs missing",
        }
        notes.append("Could not compare outputs - one or both missing")
    
    # Metadata
    time_delta = None
    if original.get("started_at") and replay.get("started_at"):
        delta = replay["started_at"] - original["started_at"]
        time_delta = delta.total_seconds() / 86400  # days
    
    return ReplayComparison(
        original_run_id=str(original["id"]),
        replay_run_id=str(replay["id"]),
        metadata={
            "original_started_at": original.get("started_at").isoformat() if original.get("started_at") else None,
            "replay_started_at": replay.get("started_at").isoformat() if replay.get("started_at") else None,
            "time_delta_days": round(time_delta, 2) if time_delta else None,
            "model_name": original.get("model_name"),
            "artifact_type": original.get("artifact_type"),
        },
        token_delta=token_delta,
        cost_delta_usd=cost_delta,
        outputs=output_comparison,
        notes=notes,
    )


def apply_overrides(
    inputs: Dict[str, str],
    overrides: Optional[ReplayOverridesRequest],
) -> Dict[str, str]:
    """Apply override values to reconstructed inputs. Returns a new dict."""
    result = dict(inputs)
    if overrides and overrides.system_prompt_override is not None:
        result["system_prompt"] = overrides.system_prompt_override
    return result


def build_overrides_metadata(
    original_inputs: Dict[str, str],
    overrides: Optional[ReplayOverridesRequest],
) -> Dict[str, str]:
    """Build audit metadata recording what was overridden."""
    if not overrides:
        return {}
    meta = {}
    if overrides.system_prompt_override is not None:
        orig_hash = hashlib.sha256(
            original_inputs.get("system_prompt", "").encode()
        ).hexdigest()[:16]
        new_hash = hashlib.sha256(
            overrides.system_prompt_override.encode()
        ).hexdigest()[:16]
        meta["system_prompt"] = f"{orig_hash} -> {new_hash}"
    if overrides.temperature is not None:
        meta["temperature"] = f"default -> {overrides.temperature}"
    if overrides.max_tokens is not None:
        meta["max_tokens"] = f"default -> {overrides.max_tokens}"
    return meta


# ================================================================================
# Replay Endpoint
# ===============================================================================

@router.post("/llm-runs/{run_id}/replay", response_model=ReplayResponse)
async def replay_llm_run(
    run_id: UUID,
    overrides: Optional[ReplayOverridesRequest] = None,
    db: AsyncSession = Depends(get_db),
    # TODO: Add admin authentication
    # current_user: User = Depends(require_admin)
):
    """
    Replay an LLM run, optionally with overrides for A/B testing.

    Creates new llm_run with is_replay=true metadata.
    Returns comparison of original vs replay.

    Supports optional overrides: system_prompt_override, temperature, max_tokens.
    When no body is provided, behaves identically to the original replay endpoint.

    **Admin only** (authentication to be added).
    """
    logger.info(f"[ADR-010] Replay requested for run {run_id}")
    
    try:
        # 1. Load original run
        original = await get_original_run(db, run_id)
        logger.info(f"[ADR-010] Loaded original run: {original['artifact_type']}, model={original['model_name']}")
        
        # 2. Reconstruct inputs
        original_inputs = await reconstruct_inputs(db, run_id)
        logger.info(f"[ADR-010] Reconstructed inputs: {list(original_inputs.keys())}")

        # 2b. Apply overrides if provided (WS-PI-0B)
        inputs = apply_overrides(original_inputs, overrides)
        overrides_meta = build_overrides_metadata(original_inputs, overrides)
        if overrides_meta:
            logger.info(f"[ADR-010] Overrides applied: {list(overrides_meta.keys())}")

        # 3. Get original output for comparison
        original_output = await get_run_output(db, run_id)
        
        # 4. Create new correlation ID for replay
        replay_correlation_id = uuid4()
        logger.info(f"[ADR-010] Replay correlation_id: {replay_correlation_id}")
        
        # 5. Set up logger for replay run
        llm_repo = PostgresLLMLogRepository(db)
        llm_logger = LLMExecutionLogger(llm_repo)
        
        # 6. Start replay run
        replay_run_id = await llm_logger.start_run(
            correlation_id=replay_correlation_id,
            project_id=original.get("project_id"),
            artifact_type=original.get("artifact_type"),
            role=original["role"],
            model_provider=original["model_provider"],
            model_name=original["model_name"],
            prompt_id=original["prompt_id"],
            prompt_version=original["prompt_version"],
            effective_prompt=inputs.get("system_prompt", ""),
        )
        logger.info(f"[ADR-010] Created replay run: {replay_run_id}")
        
        # 7. Log reconstructed inputs
        for kind, content in inputs.items():
            await llm_logger.add_input(replay_run_id, kind, content)
        
        # 8. Mark as replay in metadata via ORM
        from sqlalchemy import select as sel
        from app.api.models.llm_log import LLMRun
        
        result = await db.execute(
            sel(LLMRun).where(LLMRun.id == replay_run_id)
        )
        run_record = result.scalar_one_or_none()
        if run_record:
            existing_meta = run_record.metadata or {}
            existing_meta["is_replay"] = True
            existing_meta["original_run_id"] = str(run_id)
            if overrides_meta:
                existing_meta["overrides_applied"] = overrides_meta
            run_record.metadata = existing_meta
        await db.commit()
        
        # 9. Execute LLM call
        anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        system_prompt = inputs.get("system_prompt", "")
        user_prompt = inputs.get("user_prompt", "")
        replay_temperature = (overrides.temperature if overrides and overrides.temperature is not None else 0.5)
        replay_max_tokens = (overrides.max_tokens if overrides and overrides.max_tokens is not None else 16384)

        logger.info(f"[ADR-010] Executing replay LLM call: model={original['model_name']}, temp={replay_temperature}, max_tokens={replay_max_tokens}")

        response = anthropic_client.messages.create(
            model=original["model_name"],
            max_tokens=replay_max_tokens,
            temperature=replay_temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        
        replay_output = response.content[0].text
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        
        logger.info(f"[ADR-010] Replay LLM call complete: {input_tokens} in, {output_tokens} out")
        
        # 10. Log output
        await llm_logger.add_output(replay_run_id, "raw_text", replay_output)
        
        # 11. Complete run
        await llm_logger.complete_run(
            replay_run_id,
            status="SUCCESS",
            usage={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            }
        )
        
        # 12. Load replay run data for comparison
        replay_data = await get_original_run(db, replay_run_id)
        
        # 13. Compare runs
        comparison = compare_runs(original, replay_data, original_output, replay_output)
        
        logger.info(f"[ADR-010] Replay complete. Token delta: {comparison.token_delta}")
        
        return ReplayResponse(
            status="success",
            original_run_id=str(run_id),
            replay_run_id=str(replay_run_id),
            comparison=comparison,
        )
        
    except ValueError as e:
        logger.warning(f"[ADR-010] Replay failed: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"[ADR-010] Replay error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Replay failed: {str(e)}")


# ================================================================================
# Run Query Endpoint (WS-PI-0B)
# ===============================================================================

@router.get("/llm-runs", response_model=LLMRunQueryResponse)
async def query_llm_runs(
    project_id: Optional[UUID] = None,
    artifact_type: Optional[str] = None,
    prompt_id: Optional[str] = None,
    prompt_version: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    Query LLM runs with filtering (WS-PI-0B Step 3).

    Prompt filters apply where prompt_id/prompt_version are present in logged data;
    runs lacking these fields are excluded from prompt-filtered queries.
    """
    from sqlalchemy import select, func
    from app.api.models.llm_log import LLMRun

    limit = min(limit, 200)

    query = select(LLMRun)
    count_query = select(func.count(LLMRun.id))

    if project_id is not None:
        query = query.where(LLMRun.project_id == project_id)
        count_query = count_query.where(LLMRun.project_id == project_id)
    if artifact_type is not None:
        query = query.where(LLMRun.artifact_type == artifact_type)
        count_query = count_query.where(LLMRun.artifact_type == artifact_type)
    if prompt_id is not None:
        query = query.where(LLMRun.prompt_id == prompt_id)
        count_query = count_query.where(LLMRun.prompt_id == prompt_id)
    if prompt_version is not None:
        query = query.where(LLMRun.prompt_version == prompt_version)
        count_query = count_query.where(LLMRun.prompt_version == prompt_version)
    if status is not None:
        query = query.where(LLMRun.status == status)
        count_query = count_query.where(LLMRun.status == status)

    query = query.order_by(LLMRun.started_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    rows = result.scalars().all()

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    runs = [
        LLMRunSummary(
            id=str(row.id),
            artifact_type=row.artifact_type,
            prompt_id=row.prompt_id,
            prompt_version=row.prompt_version,
            status=row.status,
            project_id=str(row.project_id) if row.project_id else None,
            started_at=row.started_at.isoformat() if row.started_at else None,
            input_tokens=row.input_tokens,
            output_tokens=row.output_tokens,
            total_tokens=row.total_tokens,
        )
        for row in rows
    ]

    return LLMRunQueryResponse(runs=runs, total=total, limit=limit, offset=offset)


# ================================================================================
# Evaluate Endpoint (WS-PI-0B Step 5)
# ===============================================================================

class EvaluationCheckResponse(BaseModel):
    check_id: str
    status: str
    evidence: str
    notes: str

class EvaluationReportResponse(BaseModel):
    artifact_type: str
    evaluator_version: str
    checks: list[EvaluationCheckResponse]
    summary: Dict[str, int]

class EvaluateResponse(BaseModel):
    status: str
    run_id: str
    evaluation: EvaluationReportResponse


@router.post("/llm-runs/{run_id}/evaluate", response_model=EvaluateResponse)
async def evaluate_llm_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Evaluate a stored LLM run output against WS defect categories (WS-PI-0B).

    No LLM call — evaluates the stored output only.
    """
    import json
    from app.domain.services.ws_defect_evaluator import evaluate_ws

    try:
        output_text = await get_run_output(db, run_id)
        if not output_text:
            raise ValueError(f"No output found for run {run_id}")

        # Parse JSON from output (may be wrapped in markdown code blocks)
        try:
            ws_data = json.loads(output_text)
        except json.JSONDecodeError:
            # Try extracting from ```json ... ``` blocks
            import re
            match = re.search(r"```(?:json)?\s*\n(.*?)```", output_text, re.DOTALL)
            if match:
                ws_data = json.loads(match.group(1))
            else:
                raise ValueError("Output is not valid JSON and no JSON code block found")

        report = evaluate_ws(ws_data)

        return EvaluateResponse(
            status="success",
            run_id=str(run_id),
            evaluation=EvaluationReportResponse(
                artifact_type=report.artifact_type,
                evaluator_version=report.evaluator_version,
                checks=[
                    EvaluationCheckResponse(**c) for c in report.checks
                ],
                summary=report.summary,
            ),
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"[WS-PI-0B] Evaluate error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


# ================================================================================
# Batch Replay Endpoint (WS-PI-0B Step 6)
# ===============================================================================

class BatchReplayRequest(BaseModel):
    run_ids: list[UUID]
    overrides: Optional[ReplayOverridesRequest] = None

class BatchRunResult(BaseModel):
    run_id: str
    status: str
    comparison: Optional[ReplayComparison] = None
    evaluation: Optional[EvaluationReportResponse] = None
    error: Optional[str] = None

class BatchReplayResponse(BaseModel):
    status: str
    results: list[BatchRunResult]
    aggregate: Dict[str, Dict[str, int]]


@router.post("/llm-runs/batch-replay", response_model=BatchReplayResponse)
async def batch_replay_llm_runs(
    request: BatchReplayRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Replay multiple LLM runs with the same overrides (WS-PI-0B).

    Executes sequentially to avoid rate limits.
    Returns per-run comparisons + evaluations + aggregate defect counts.
    """
    import json
    from app.domain.services.ws_defect_evaluator import evaluate_ws

    results = []
    # Aggregate counts by check_id
    agg: Dict[str, Dict[str, int]] = {}

    for rid in request.run_ids:
        try:
            # Replay
            original = await get_original_run(db, rid)
            original_inputs = await reconstruct_inputs(db, rid)
            inputs = apply_overrides(original_inputs, request.overrides)
            overrides_meta = build_overrides_metadata(original_inputs, request.overrides)
            original_output = await get_run_output(db, rid)

            replay_correlation_id = uuid4()
            llm_repo = PostgresLLMLogRepository(db)
            llm_logger = LLMExecutionLogger(llm_repo)

            replay_run_id = await llm_logger.start_run(
                correlation_id=replay_correlation_id,
                project_id=original.get("project_id"),
                artifact_type=original.get("artifact_type"),
                role=original["role"],
                model_provider=original["model_provider"],
                model_name=original["model_name"],
                prompt_id=original["prompt_id"],
                prompt_version=original["prompt_version"],
                effective_prompt=inputs.get("system_prompt", ""),
            )

            for kind, content in inputs.items():
                await llm_logger.add_input(replay_run_id, kind, content)

            # Tag metadata
            from sqlalchemy import select as sel
            from app.api.models.llm_log import LLMRun
            result = await db.execute(sel(LLMRun).where(LLMRun.id == replay_run_id))
            run_record = result.scalar_one_or_none()
            if run_record:
                existing_meta = run_record.metadata or {}
                existing_meta["is_replay"] = True
                existing_meta["original_run_id"] = str(rid)
                existing_meta["batch_replay"] = True
                if overrides_meta:
                    existing_meta["overrides_applied"] = overrides_meta
                run_record.metadata = existing_meta
            await db.commit()

            # Execute LLM call
            anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            system_prompt = inputs.get("system_prompt", "")
            user_prompt = inputs.get("user_prompt", "")
            replay_temperature = (
                request.overrides.temperature
                if request.overrides and request.overrides.temperature is not None
                else 0.5
            )
            replay_max_tokens = (
                request.overrides.max_tokens
                if request.overrides and request.overrides.max_tokens is not None
                else 16384
            )

            response = anthropic_client.messages.create(
                model=original["model_name"],
                max_tokens=replay_max_tokens,
                temperature=replay_temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            replay_output = response.content[0].text
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens

            await llm_logger.add_output(replay_run_id, "raw_text", replay_output)
            await llm_logger.complete_run(
                replay_run_id,
                status="SUCCESS",
                usage={
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                },
            )

            replay_data = await get_original_run(db, replay_run_id)
            comparison = compare_runs(original, replay_data, original_output, replay_output)

            # Evaluate replay output
            eval_report = None
            try:
                ws_data = json.loads(replay_output)
                report = evaluate_ws(ws_data)
                eval_report = EvaluationReportResponse(
                    artifact_type=report.artifact_type,
                    evaluator_version=report.evaluator_version,
                    checks=[EvaluationCheckResponse(**c) for c in report.checks],
                    summary=report.summary,
                )
                # Aggregate
                for c in report.checks:
                    if c["check_id"] not in agg:
                        agg[c["check_id"]] = {"passed": 0, "failed": 0, "advisory": 0, "not_evaluable": 0}
                    status_key = "passed" if c["status"] == "pass" else c["status"]
                    if status_key in agg[c["check_id"]]:
                        agg[c["check_id"]][status_key] += 1
            except (json.JSONDecodeError, Exception):
                pass  # Evaluation is best-effort on batch

            results.append(BatchRunResult(
                run_id=str(rid),
                status="success",
                comparison=comparison,
                evaluation=eval_report,
            ))

        except Exception as e:
            logger.error(f"[WS-PI-0B] Batch replay error for {rid}: {e}", exc_info=True)
            results.append(BatchRunResult(
                run_id=str(rid),
                status="error",
                error=str(e),
            ))

    return BatchReplayResponse(
        status="success",
        results=results,
        aggregate=agg,
    )


# ================================================================================
# Prompt Assembly Debug Endpoint (ADR-041)
# ===============================================================================

class PromptAssemblyRequest(BaseModel):
    """Request to assemble a prompt."""
    task_ref: str
    includes: Dict[str, str] = {}


class PromptAssemblyResponse(BaseModel):
    """Response from prompt assembly."""
    task_ref: str
    content: str
    content_hash: str
    includes_resolved: Dict[str, str]
    assembled_at: str
    content_length: int


def get_prompt_assembly_service():
    """Dependency for PromptAssemblyService."""
    from app.domain.services.prompt_assembly_service import PromptAssemblyService
    return PromptAssemblyService()


@router.post("/prompts/assemble", response_model=PromptAssemblyResponse)
async def assemble_prompt(request: PromptAssemblyRequest):
    """
    Assemble a prompt from template and includes.
    
    For testing ADR-041 prompt template assembly.

    Example request:
    ```json
    {
        "task_ref": "clarification_questions_generator",
        "includes": {
            "PGC_CONTEXT": "combine-config/prompts/pgc/project_discovery.v1/releases/1.0.0/pgc.prompt.txt",
            "OUTPUT_SCHEMA": "combine-config/schemas/clarification_question_set/releases/2.0.0/schema.json"
        }
    }
    ```
    """
    from app.domain.services.prompt_assembly_service import PromptAssemblyService
    from app.domain.prompt.errors import PromptAssemblyError
    
    service = PromptAssemblyService()
    
    try:
        result = service.assemble(
            task_ref=request.task_ref,
            includes=request.includes,
            correlation_id=str(uuid4()),
        )
        
        return PromptAssemblyResponse(
            task_ref=result.task_ref,
            content=result.content,
            content_hash=result.content_hash,
            includes_resolved=result.includes_resolved,
            assembled_at=result.assembled_at.isoformat(),
            content_length=len(result.content),
        )
        
    except PromptAssemblyError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[ADR-041] Assembly error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Assembly failed: {str(e)}")


@router.get("/prompts/workflows/{workflow_id}/nodes/{node_id}/assemble", response_model=PromptAssemblyResponse)
async def assemble_prompt_from_workflow(workflow_id: str, node_id: str):
    """
    Assemble a prompt using workflow node configuration.
    
    Loads the workflow, finds the node, and assembles the prompt
    using the node's task_ref and includes map.
    
    Example: GET /api/admin/prompts/workflows/pm_discovery/nodes/pgc/assemble
    """
    from app.domain.services.prompt_assembly_service import PromptAssemblyService
    from app.domain.prompt.errors import PromptAssemblyError
    
    service = PromptAssemblyService()
    
    try:
        result = service.assemble_from_workflow(
            workflow_id=workflow_id,
            node_id=node_id,
            correlation_id=str(uuid4()),
        )
        
        return PromptAssemblyResponse(
            task_ref=result.task_ref,
            content=result.content,
            content_hash=result.content_hash,
            includes_resolved=result.includes_resolved,
            assembled_at=result.assembled_at.isoformat(),
            content_length=len(result.content),
        )
        
    except PromptAssemblyError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[ADR-041] Assembly error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Assembly failed: {str(e)}")


@router.get("/prompts/workflows")
async def list_workflows():
    """List available workflows with assembler-compatible nodes."""
    from app.domain.services.prompt_assembly_service import PromptAssemblyService
    
    service = PromptAssemblyService()
    workflows = service.list_workflows()
    
    result = []
    for wf_id in workflows:
        try:
            nodes = service.list_workflow_nodes(wf_id)
            # Filter to nodes that have includes (assembler-compatible)
            assembler_nodes = []
            for node_id in nodes:
                try:
                    node = service.get_workflow_node(wf_id, node_id)
                    if node.includes:
                        assembler_nodes.append({
                            "node_id": node.node_id,
                            "task_ref": node.task_ref,
                            "includes": list(node.includes.keys()),
                        })
                except Exception:
                    pass

            if assembler_nodes:
                result.append({
                    "workflow_id": wf_id,
                    "nodes_with_includes": assembler_nodes,
                })
        except Exception:
            pass
    
    return {"workflows": result}