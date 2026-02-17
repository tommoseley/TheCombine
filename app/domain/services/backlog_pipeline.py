"""
Backlog Compilation Pipeline service.

Orchestrates the full BCP sequence:
1. Load IntentPacket
2. Run Backlog Generator DCW
3. Validate graph (dependency, hierarchy, cycles)
4. Derive ExecutionPlan (mechanical)
5. Run Plan Explanation DCW (optional)
6. Store pipeline_run metadata

"LLMs generate. Machines order."

WS-BCP-004: Task 9, Task 10.
"""

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.domain.services.graph_validator import (
    validate_backlog,
    BacklogValidationResult,
    DependencyError,
    HierarchyError,
    CycleTrace,
)
from app.domain.services.backlog_ordering import (
    compute_backlog_hash,
    derive_execution_plan,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class StageResult:
    """Result of a single pipeline stage."""
    status: str  # "completed" | "failed" | "skipped"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    execution_id: Optional[str] = None
    document_id: Optional[str] = None
    error: Optional[str] = None


@dataclass
class PipelineResult:
    """Result of a full pipeline run."""
    status: str          # "completed" | "failed"
    run_id: str
    intent_id: str
    stage_reached: str   # Last stage attempted
    backlog_hash: Optional[str] = None
    plan_id: Optional[str] = None
    explanation_id: Optional[str] = None
    errors: Optional[Dict[str, Any]] = None
    stages: Dict[str, StageResult] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Hash functions (Task 10)
# ---------------------------------------------------------------------------

def compute_intent_hash(intent_content: dict) -> str:
    """SHA-256 of canonical JSON of intent content."""
    canonical = json.dumps(intent_content, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_plan_hash(ordered_ids: list[str], waves: list[list[str]]) -> str:
    """SHA-256 of ordered_backlog_ids + waves (canonical JSON)."""
    data = {"ordered_backlog_ids": ordered_ids, "waves": waves}
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Pipeline service
# ---------------------------------------------------------------------------

class BacklogPipelineService:
    """
    Orchestrates the full Backlog Compilation Pipeline.

    Dependencies are injected for testability:
    - db_session: async SQLAlchemy session for document queries/persistence
    - plan_executor: PlanExecutor instance for running DCWs
    """

    def __init__(self, db_session, plan_executor):
        self._db = db_session
        self._executor = plan_executor

    async def run(
        self,
        project_id: str,
        intent_id: str,
        skip_explanation: bool = False,
    ) -> PipelineResult:
        """Run the full pipeline from IntentPacket to ExecutionPlan.

        Args:
            project_id: Project UUID
            intent_id: IntentPacket document UUID
            skip_explanation: If True, skip the explanation DCW (step 5)

        Returns:
            PipelineResult with status, artifacts, and replay metadata
        """
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        stages: Dict[str, StageResult] = {}

        # ---------------------------------------------------------------
        # Step 1: Load IntentPacket
        # ---------------------------------------------------------------
        intent_content = await self._load_intent(intent_id)
        if intent_content is None:
            return PipelineResult(
                status="failed",
                run_id=run_id,
                intent_id=intent_id,
                stage_reached="load_intent",
                errors={"error": "intent_not_found", "detail": f"IntentPacket {intent_id} not found"},
                stages=stages,
            )

        intent_hash = compute_intent_hash(intent_content)

        # ---------------------------------------------------------------
        # Step 2: Run Backlog Generator DCW
        # ---------------------------------------------------------------
        gen_stage = StageResult(status="running", started_at=_now())
        try:
            gen_result = await self._run_dcw(
                project_id=project_id,
                document_type="backlog_item",
                input_documents={"intent_packet": intent_content},
            )
            gen_stage.completed_at = _now()
            gen_stage.execution_id = gen_result.get("execution_id")

            if gen_result["terminal_outcome"] != "stabilized":
                gen_stage.status = "failed"
                gen_stage.error = "backlog_generation_blocked"
                stages["generation"] = gen_stage
                return PipelineResult(
                    status="failed",
                    run_id=run_id,
                    intent_id=intent_id,
                    stage_reached="generation",
                    errors={"error": "backlog_generation_failed", "stage": "generation"},
                    stages=stages,
                    metadata={"intent_hash": intent_hash, "generator_version": "1.0.0"},
                )

            gen_stage.status = "completed"
            gen_stage.document_id = gen_result.get("document_id")
            stages["generation"] = gen_stage

        except Exception as e:
            gen_stage.status = "failed"
            gen_stage.completed_at = _now()
            gen_stage.error = str(e)
            stages["generation"] = gen_stage
            return PipelineResult(
                status="failed",
                run_id=run_id,
                intent_id=intent_id,
                stage_reached="generation",
                errors={"error": "generation_exception", "detail": str(e)},
                stages=stages,
                metadata={"intent_hash": intent_hash, "generator_version": "1.0.0"},
            )

        # Extract backlog items from produced document
        backlog_content = await self._load_latest_document(project_id, "backlog_item")
        if not backlog_content or "items" not in backlog_content:
            stages["generation"] = gen_stage
            return PipelineResult(
                status="failed",
                run_id=run_id,
                intent_id=intent_id,
                stage_reached="generation",
                errors={"error": "no_backlog_items", "detail": "Backlog generator produced no items"},
                stages=stages,
                metadata={"intent_hash": intent_hash, "generator_version": "1.0.0"},
            )

        items = backlog_content["items"]

        # ---------------------------------------------------------------
        # Step 3: Validate graph
        # ---------------------------------------------------------------
        val_stage = StageResult(status="running", started_at=_now())
        validation = validate_backlog(items)
        val_stage.completed_at = _now()

        if not validation.valid:
            val_stage.status = "failed"
            stages["validation"] = val_stage
            return PipelineResult(
                status="failed",
                run_id=run_id,
                intent_id=intent_id,
                stage_reached="validation",
                errors={
                    "error": "graph_validation_failed",
                    "dependency_errors": [
                        {"item_id": e.item_id, "error_type": e.error_type, "detail": e.detail}
                        for e in validation.dependency_errors
                    ],
                    "hierarchy_errors": [
                        {"item_id": e.item_id, "error_type": e.error_type, "detail": e.detail}
                        for e in validation.hierarchy_errors
                    ],
                    "cycle_traces": [
                        {"cycle": t.cycle} for t in validation.cycle_traces
                    ],
                },
                stages=stages,
                metadata={
                    "intent_hash": intent_hash,
                    "generator_version": "1.0.0",
                },
            )

        val_stage.status = "completed"
        stages["validation"] = val_stage

        # ---------------------------------------------------------------
        # Step 4: Derive ExecutionPlan (mechanical)
        # ---------------------------------------------------------------
        deriv_stage = StageResult(status="running", started_at=_now())
        plan_data = derive_execution_plan(items, intent_id=intent_id, run_id=run_id)
        b_hash = plan_data["backlog_hash"]

        # Check for existing plan with same backlog_hash
        existing_plan = await self._find_execution_plan_by_hash(project_id, b_hash)
        if existing_plan:
            deriv_stage.status = "completed"
            deriv_stage.completed_at = _now()
            deriv_stage.document_id = existing_plan["id"]
            stages["derivation"] = deriv_stage
            plan_id = existing_plan["id"]
            plan_content = existing_plan["content"]
            logger.info(f"Reusing existing execution plan for backlog_hash {b_hash[:12]}...")
        else:
            plan_id = await self._persist_document(
                project_id=project_id,
                doc_type_id="execution_plan",
                title=f"Execution Plan: {len(items)} items",
                content=plan_data,
            )
            deriv_stage.status = "completed"
            deriv_stage.completed_at = _now()
            deriv_stage.document_id = plan_id
            stages["derivation"] = deriv_stage
            plan_content = plan_data

        plan_hash = compute_plan_hash(
            plan_content["ordered_backlog_ids"],
            plan_content["waves"],
        )

        # ---------------------------------------------------------------
        # Step 5: Run Plan Explanation DCW (optional)
        # ---------------------------------------------------------------
        explanation_id = None
        if not skip_explanation:
            exp_stage = StageResult(status="running", started_at=_now())
            try:
                exp_result = await self._run_dcw(
                    project_id=project_id,
                    document_type="plan_explanation",
                    input_documents={
                        "execution_plan": plan_content,
                        "backlog_items": items,
                    },
                )
                exp_stage.completed_at = _now()
                exp_stage.execution_id = exp_result.get("execution_id")

                if exp_result["terminal_outcome"] == "stabilized":
                    exp_stage.status = "completed"
                    exp_stage.document_id = exp_result.get("document_id")
                    explanation_id = exp_result.get("document_id")
                else:
                    exp_stage.status = "failed"
                    exp_stage.error = "explanation_blocked"
                    logger.warning("Plan explanation DCW blocked — pipeline continues")

            except Exception as e:
                exp_stage.status = "failed"
                exp_stage.completed_at = _now()
                exp_stage.error = str(e)
                logger.warning(f"Plan explanation failed: {e} — pipeline continues")

            stages["explanation"] = exp_stage
        else:
            stages["explanation"] = StageResult(status="skipped")

        # ---------------------------------------------------------------
        # Step 6: Build replay metadata and result
        # ---------------------------------------------------------------
        replay_metadata = {
            "intent_hash": intent_hash,
            "source_hash": intent_hash,  # Generalized: parent structural hash for staleness detection
            "source_id": intent_id,      # What this run generated from
            "backlog_hash": b_hash,
            "plan_hash": plan_hash,
            "prompt_version": "1.0.0",
            "model_version": None,  # Populated by LLM execution logger at runtime
            "generator_version": "1.0.0",
        }

        result = PipelineResult(
            status="completed",
            run_id=run_id,
            intent_id=intent_id,
            stage_reached="completed",
            backlog_hash=b_hash,
            plan_id=plan_id,
            explanation_id=explanation_id,
            stages=stages,
            metadata=replay_metadata,
        )

        # Persist pipeline_run document
        await self._persist_pipeline_run(project_id, result)

        return result

    # -------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------

    async def _load_intent(self, intent_id: str) -> Optional[dict]:
        """Load IntentPacket content by document ID."""
        from sqlalchemy import select
        from app.api.models.document import Document
        from uuid import UUID

        try:
            doc_uuid = UUID(intent_id)
        except ValueError:
            return None

        result = await self._db.execute(
            select(Document).where(
                Document.id == doc_uuid,
                Document.doc_type_id == "intent_packet",
            )
        )
        doc = result.scalar_one_or_none()
        return doc.content if doc else None

    async def _load_latest_document(self, project_id: str, doc_type_id: str) -> Optional[dict]:
        """Load the latest document of a given type for a project."""
        from sqlalchemy import select
        from app.api.models.document import Document
        from uuid import UUID

        try:
            project_uuid = UUID(project_id)
        except ValueError:
            return None

        result = await self._db.execute(
            select(Document).where(
                Document.space_id == project_uuid,
                Document.doc_type_id == doc_type_id,
                Document.is_latest == True,
            )
        )
        doc = result.scalar_one_or_none()
        return doc.content if doc else None

    async def _find_execution_plan_by_hash(
        self, project_id: str, backlog_hash: str
    ) -> Optional[dict]:
        """Find an existing execution_plan document with matching backlog_hash."""
        from sqlalchemy import select
        from app.api.models.document import Document
        from uuid import UUID

        try:
            project_uuid = UUID(project_id)
        except ValueError:
            return None

        result = await self._db.execute(
            select(Document).where(
                Document.space_id == project_uuid,
                Document.doc_type_id == "execution_plan",
                Document.is_latest == True,
            )
        )
        doc = result.scalar_one_or_none()
        if doc and doc.content and doc.content.get("backlog_hash") == backlog_hash:
            return {"id": str(doc.id), "content": doc.content}
        return None

    async def _persist_document(
        self,
        project_id: str,
        doc_type_id: str,
        title: str,
        content: dict,
        instance_id: Optional[str] = None,
    ) -> str:
        """Persist a new document and return its ID."""
        from app.api.models.document import Document
        from uuid import UUID

        doc = Document(
            space_type="project",
            space_id=UUID(project_id),
            doc_type_id=doc_type_id,
            title=title,
            content=content,
            version=1,
            is_latest=True,
            status="complete",
            lifecycle_state="complete",
            instance_id=instance_id,
        )
        self._db.add(doc)
        await self._db.flush()
        return str(doc.id)

    async def _persist_pipeline_run(
        self, project_id: str, result: PipelineResult
    ) -> str:
        """Persist pipeline_run metadata document."""
        content = {
            "run_id": result.run_id,
            "intent_id": result.intent_id,
            "status": result.status,
            "stage_reached": result.stage_reached,
            "stages": {
                name: {
                    "status": stage.status,
                    "started_at": stage.started_at,
                    "completed_at": stage.completed_at,
                    "execution_id": stage.execution_id,
                    "document_id": stage.document_id,
                    "error": stage.error,
                }
                for name, stage in result.stages.items()
            },
            "replay_metadata": result.metadata,
            "errors": result.errors,
        }

        return await self._persist_document(
            project_id=project_id,
            doc_type_id="pipeline_run",
            title=f"Pipeline Run {result.run_id}",
            content=content,
            instance_id=result.run_id,
        )

    async def _run_dcw(
        self,
        project_id: str,
        document_type: str,
        input_documents: dict,
    ) -> dict:
        """Run a DCW to completion and return the result.

        Returns:
            Dict with terminal_outcome, execution_id, document_id
        """
        initial_context = {"input_documents": input_documents}

        state = await self._executor.start_execution(
            project_id=project_id,
            document_type=document_type,
            initial_context=initial_context,
        )

        state = await self._executor.run_to_completion_or_pause(state.execution_id)

        terminal_outcome = state.terminal_outcome or "blocked"
        if state.status.value == "failed":
            terminal_outcome = "blocked"

        # Get the produced document ID if stabilized
        document_id = None
        if terminal_outcome == "stabilized":
            doc = await self._load_latest_document(
                project_id, document_type
            )
            if doc:
                # We need the document ID, not content, for the result
                from sqlalchemy import select
                from app.api.models.document import Document
                from uuid import UUID
                result = await self._db.execute(
                    select(Document.id).where(
                        Document.space_id == UUID(project_id),
                        Document.doc_type_id == document_type,
                        Document.is_latest == True,
                    )
                )
                row = result.scalar_one_or_none()
                if row:
                    document_id = str(row)

        return {
            "terminal_outcome": terminal_outcome,
            "execution_id": state.execution_id,
            "document_id": document_id,
        }


def _now() -> str:
    """UTC timestamp as ISO string."""
    return datetime.now(timezone.utc).isoformat()
