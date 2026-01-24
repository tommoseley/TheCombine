"""
Admin API routes for The Combine.

ADR-010 Week 3: LLM execution replay functionality.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID, uuid4
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel
import hashlib
import json
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


# ================================================================================
# Replay Endpoint
# ===============================================================================

@router.post("/llm-runs/{run_id}/replay", response_model=ReplayResponse)
async def replay_llm_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    # TODO: Add admin authentication
    # current_user: User = Depends(require_admin)
):
    """
    Replay an LLM run with identical inputs.
    
    Creates new llm_run with is_replay=true metadata.
    Returns comparison of original vs replay.
    
    **Admin only** (authentication to be added).
    """
    logger.info(f"[ADR-010] Replay requested for run {run_id}")
    
    try:
        # 1. Load original run
        original = await get_original_run(db, run_id)
        logger.info(f"[ADR-010] Loaded original run: {original['artifact_type']}, model={original['model_name']}")
        
        # 2. Reconstruct inputs
        inputs = await reconstruct_inputs(db, run_id)
        logger.info(f"[ADR-010] Reconstructed inputs: {list(inputs.keys())}")
        
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
            run_record.metadata = existing_meta
        await db.commit()
        
        # 9. Execute LLM call
        anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        system_prompt = inputs.get("system_prompt", "")
        user_prompt = inputs.get("user_prompt", "")
        
        logger.info(f"[ADR-010] Executing replay LLM call: model={original['model_name']}")
        
        response = anthropic_client.messages.create(
            model=original["model_name"],
            max_tokens=16384,
            temperature=0.5,
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
        "task_ref": "Clarification Questions Generator v1.0",
        "includes": {
            "PGC_CONTEXT": "seed/prompts/pgc-contexts/project_discovery.v1.txt",
            "OUTPUT_SCHEMA": "seed/schemas/clarification_question_set.v2.json"
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
                except:
                    pass
            
            if assembler_nodes:
                result.append({
                    "workflow_id": wf_id,
                    "nodes_with_includes": assembler_nodes,
                })
        except:
            pass
    
    return {"workflows": result}