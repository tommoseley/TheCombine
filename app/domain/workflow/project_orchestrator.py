"""Project Orchestrator for Production Line (ADR-043 Phase 4).

Coordinates document production across an entire project, respecting
the dependency graph and enabling parallel execution where possible.

The orchestrator implements [Run Full Line] functionality:
1. Load document dependency graph
2. Identify documents with satisfied dependencies
3. Start production for each (parallel where allowed)
4. Listen for stabilization events
5. Start next tier when dependencies clear
6. Complete when all stabilized or halted
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.document import Document
from app.api.models.workflow_execution import WorkflowExecution
from app.domain.workflow.production_state import ProductionState
from app.domain.workflow.plan_registry import get_plan_registry

logger = logging.getLogger(__name__)


class OrchestrationStatus(str, Enum):
    """Status of the orchestration run."""

    RUNNING = "running"
    PAUSED = "paused"  # One or more tracks awaiting operator
    COMPLETED = "completed"  # All documents stabilized
    HALTED = "halted"  # One or more tracks halted
    FAILED = "failed"  # Orchestration error


@dataclass
class TrackState:
    """State of a single document track in the orchestration."""

    document_type: str
    state: ProductionState = ProductionState.READY_FOR_PRODUCTION
    execution_id: Optional[str] = None
    blocked_by: List[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


@dataclass
class OrchestrationState:
    """Full state of an orchestration run."""

    orchestration_id: str
    project_id: str
    status: OrchestrationStatus = OrchestrationStatus.RUNNING
    tracks: Dict[str, TrackState] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


class ProjectOrchestrator:
    """Orchestrates document production across a project.

    The orchestrator manages the [Run Full Line] operation, coordinating
    multiple document workflows according to their dependency graph.

    Usage:
        orchestrator = ProjectOrchestrator(db)
        result = await orchestrator.run_full_line(project_id)
    """

    def __init__(self, db: AsyncSession):
        """Initialize orchestrator.

        Args:
            db: Database session for queries and state persistence
        """
        self.db = db
        self._state: Optional[OrchestrationState] = None

    async def run_full_line(
        self,
        project_id: str,
        document_types: Optional[List[str]] = None,
    ) -> OrchestrationState:
        """Run production for an entire project.

        Starts document production in dependency order, running documents
        in parallel where their dependencies are satisfied.

        Args:
            project_id: Project to run production for
            document_types: Optional subset of document types to produce.
                           If None, produces all document types.

        Returns:
            OrchestrationState with final status and track states
        """
        from uuid import uuid4

        orchestration_id = f"orch-{uuid4().hex[:12]}"
        logger.info(
            f"Starting full line production for project {project_id} "
            f"(orchestration {orchestration_id})"
        )

        # Initialize state
        self._state = OrchestrationState(
            orchestration_id=orchestration_id,
            project_id=project_id,
        )

        try:
            # Get dependency graph
            dep_graph = await self._get_dependency_graph(document_types)
            logger.info(f"Loaded dependency graph with {len(dep_graph)} document types")

            # Get existing stabilized documents
            stabilized = await self._get_stabilized_documents(project_id)
            logger.info(f"Found {len(stabilized)} already stabilized documents")

            # Initialize tracks
            for doc_type, requires in dep_graph.items():
                if doc_type in stabilized:
                    self._state.tracks[doc_type] = TrackState(
                        document_type=doc_type,
                        state=ProductionState.STABILIZED,
                        completed_at=datetime.now(timezone.utc),
                    )
                else:
                    missing = [r for r in requires if r not in stabilized]
                    self._state.tracks[doc_type] = TrackState(
                        document_type=doc_type,
                        state=ProductionState.BLOCKED if missing else ProductionState.QUEUED,
                        blocked_by=missing,
                    )

            # Run until all complete or stuck
            await self._run_orchestration_loop(project_id, dep_graph)

            # Determine final status
            self._state.completed_at = datetime.now(timezone.utc)
            self._state.status = self._calculate_final_status()

            logger.info(
                f"Orchestration {orchestration_id} completed with status "
                f"{self._state.status.value}"
            )

            return self._state

        except Exception as e:
            logger.error(f"Orchestration failed: {e}", exc_info=True)
            if self._state:
                self._state.status = OrchestrationStatus.FAILED
                self._state.completed_at = datetime.now(timezone.utc)
            raise

    async def _get_dependency_graph(
        self,
        document_types: Optional[List[str]] = None,
    ) -> Dict[str, List[str]]:
        """Get document dependency graph from plan registry.

        Returns:
            Dict mapping document_type -> list of required input types
        """
        registry = get_plan_registry()
        plans = registry.list_plans()

        dep_graph = {}
        for plan in plans:
            if document_types and plan.document_type not in document_types:
                continue
            dep_graph[plan.document_type] = plan.requires_inputs or []

        return dep_graph

    async def _get_stabilized_documents(self, project_id: str) -> Set[str]:
        """Get set of document types that are already stabilized.

        Args:
            project_id: Project ID (UUID or project_id string)

        Returns:
            Set of stabilized document type IDs
        """
        # Resolve project UUID
        from app.api.models.project import Project

        try:
            project_uuid = UUID(project_id)
        except ValueError:
            result = await self.db.execute(
                select(Project).where(Project.project_id == project_id)
            )
            project = result.scalar_one_or_none()
            if not project:
                return set()
            project_uuid = project.id

        # Query stabilized documents
        result = await self.db.execute(
            select(Document)
            .where(Document.space_type == "project")
            .where(Document.space_id == project_uuid)
            .where(Document.is_latest == True)
            .where(Document.status.in_(["stabilized", "complete", "success", "active"]))
        )

        return {doc.doc_type_id for doc in result.scalars().all()}

    async def _run_orchestration_loop(
        self,
        project_id: str,
        dep_graph: Dict[str, List[str]],
    ) -> None:
        """Main orchestration loop.

        Continues until:
        - All documents stabilized
        - All remaining documents blocked/halted
        - Execution paused (awaiting operator)
        """
        max_iterations = 100  # Safety limit
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # Find documents ready to start (queued with satisfied deps)
            ready = self._find_ready_documents()
            if not ready:
                # Check if we're stuck or done
                if self._is_complete_or_stuck():
                    break
                # Wait for running executions
                await self._wait_for_completions(project_id)
                continue

            # Start production for ready documents
            logger.info(f"Starting production for {len(ready)} documents: {ready}")
            tasks = [
                self._start_document_production(project_id, doc_type)
                for doc_type in ready
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

            # Run executions to completion or pause
            await self._run_active_executions()

            # Update blocked states based on new stabilizations
            self._update_blocked_states()

        if iteration >= max_iterations:
            logger.warning(f"Orchestration hit iteration limit ({max_iterations})")

    def _find_ready_documents(self) -> List[str]:
        """Find documents ready to start production.

        A document is ready if:
        - State is QUEUED (not already started)
        - All required dependencies are stabilized
        """
        if not self._state:
            return []

        stabilized = {
            dt
            for dt, track in self._state.tracks.items()
            if track.state == ProductionState.STABILIZED
        }

        ready = []
        for doc_type, track in self._state.tracks.items():
            if track.state != ProductionState.QUEUED:
                continue
            if all(dep in stabilized for dep in track.blocked_by):
                ready.append(doc_type)

        return ready

    def _is_complete_or_stuck(self) -> bool:
        """Check if orchestration is complete or stuck.

        Returns True if:
        - All documents are in terminal state (stabilized/halted)
        - OR remaining documents are blocked/awaiting operator
        """
        if not self._state:
            return True

        for track in self._state.tracks.values():
            # If any track is still runnable, not complete
            if track.state in [
                ProductionState.QUEUED,
                ProductionState.BINDING,
                ProductionState.ASSEMBLING,
                ProductionState.AUDITING,
                ProductionState.REMEDIATING,
            ]:
                # Check if actually running
                if track.execution_id:
                    return False

        return True

    async def _start_document_production(
        self,
        project_id: str,
        document_type: str,
    ) -> None:
        """Start production for a single document.

        Uses the document-workflows API to start execution.
        """
        from app.domain.workflow.plan_executor import PlanExecutor
        from app.domain.workflow.pg_state_persistence import PgStatePersistence
        from app.domain.workflow.nodes.llm_executors import create_llm_executors

        if not self._state:
            return

        track = self._state.tracks.get(document_type)
        if not track:
            return

        try:
            # Create executor
            executors = await create_llm_executors(self.db)
            executor = PlanExecutor(
                persistence=PgStatePersistence(self.db),
                plan_registry=get_plan_registry(),
                executors=executors,
                db_session=self.db,
            )

            # Start execution
            state = await executor.start_execution(
                project_id=project_id,
                document_type=document_type,
                initial_context={},
            )

            # Update track state
            track.execution_id = state.execution_id
            track.state = ProductionState.BINDING
            track.started_at = datetime.now(timezone.utc)
            track.blocked_by = []

            logger.info(
                f"Started production for {document_type}: "
                f"execution {state.execution_id}"
            )

            # Emit event for UI
            await self._emit_event(
                "track_started",
                {
                    "document_type": document_type,
                    "execution_id": state.execution_id,
                    "state": track.state.value,
                },
            )

        except Exception as e:
            logger.error(f"Failed to start {document_type}: {e}")
            track.state = ProductionState.HALTED
            track.error = str(e)

    async def _run_active_executions(self) -> None:
        """Run all active executions to completion or pause."""
        from app.domain.workflow.plan_executor import PlanExecutor
        from app.domain.workflow.pg_state_persistence import PgStatePersistence
        from app.domain.workflow.nodes.llm_executors import create_llm_executors
        from app.domain.workflow.document_workflow_state import DocumentWorkflowStatus

        if not self._state:
            return

        for doc_type, track in self._state.tracks.items():
            if not track.execution_id:
                continue
            if track.state in [
                ProductionState.STABILIZED,
                ProductionState.HALTED,
                ProductionState.AWAITING_OPERATOR,
            ]:
                continue

            try:
                # Create executor for this execution
                executors = await create_llm_executors(self.db)
                executor = PlanExecutor(
                    persistence=PgStatePersistence(self.db),
                    plan_registry=get_plan_registry(),
                    executors=executors,
                    db_session=self.db,
                )

                # Run to completion or pause
                state = await executor.run_to_completion_or_pause(track.execution_id)

                # Update track based on result
                if state.status == DocumentWorkflowStatus.COMPLETED:
                    track.state = ProductionState.STABILIZED
                    track.completed_at = datetime.now(timezone.utc)
                    logger.info(f"{doc_type} stabilized")
                    await self._emit_event(
                        "track_stabilized",
                        {"document_type": doc_type, "execution_id": track.execution_id},
                    )

                elif state.status == DocumentWorkflowStatus.PAUSED:
                    track.state = ProductionState.AWAITING_OPERATOR
                    logger.info(f"{doc_type} awaiting operator input")
                    await self._emit_event(
                        "line_stopped",
                        {
                            "document_type": doc_type,
                            "execution_id": track.execution_id,
                            "reason": "clarification_required",
                        },
                    )

                elif state.status == DocumentWorkflowStatus.FAILED:
                    track.state = ProductionState.HALTED
                    track.error = state.terminal_outcome
                    logger.info(f"{doc_type} halted: {state.terminal_outcome}")

                else:
                    # Still running - map current node to state
                    current_node = state.current_node_id or ""
                    if "qa" in current_node.lower():
                        track.state = ProductionState.AUDITING
                    elif "remediat" in current_node.lower():
                        track.state = ProductionState.REMEDIATING
                    else:
                        track.state = ProductionState.ASSEMBLING

            except Exception as e:
                logger.error(f"Error running {doc_type}: {e}")
                track.state = ProductionState.HALTED
                track.error = str(e)

    async def _wait_for_completions(self, project_id: str) -> None:
        """Wait for running executions to make progress.

        This is a simple polling approach - can be enhanced with SSE later.
        """
        # Short delay to allow executions to progress
        await asyncio.sleep(1.0)

        # Refresh execution states from database
        if not self._state:
            return

        for doc_type, track in self._state.tracks.items():
            if not track.execution_id:
                continue

            result = await self.db.execute(
                select(WorkflowExecution).where(
                    WorkflowExecution.execution_id == track.execution_id
                )
            )
            execution = result.scalar_one_or_none()
            if not execution:
                continue

            # Update track state based on execution status
            if execution.status == "completed":
                track.state = ProductionState.STABILIZED
                track.completed_at = datetime.now(timezone.utc)
            elif execution.status == "paused":
                track.state = ProductionState.AWAITING_OPERATOR
            elif execution.status == "failed":
                track.state = ProductionState.HALTED

    def _update_blocked_states(self) -> None:
        """Update blocked_by lists based on current stabilizations."""
        if not self._state:
            return

        stabilized = {
            dt
            for dt, track in self._state.tracks.items()
            if track.state == ProductionState.STABILIZED
        }

        for track in self._state.tracks.values():
            if track.state == ProductionState.BLOCKED:
                track.blocked_by = [
                    dep for dep in track.blocked_by if dep not in stabilized
                ]
                if not track.blocked_by:
                    track.state = ProductionState.QUEUED

    def _calculate_final_status(self) -> OrchestrationStatus:
        """Calculate final orchestration status from track states."""
        if not self._state:
            return OrchestrationStatus.FAILED

        has_halted = False
        has_awaiting = False
        all_complete = True

        for track in self._state.tracks.values():
            if track.state == ProductionState.HALTED:
                has_halted = True
            if track.state == ProductionState.AWAITING_OPERATOR:
                has_awaiting = True
            if track.state not in [ProductionState.STABILIZED, ProductionState.HALTED]:
                all_complete = False

        if has_awaiting:
            return OrchestrationStatus.PAUSED
        if has_halted:
            return OrchestrationStatus.HALTED
        if all_complete:
            return OrchestrationStatus.COMPLETED
        return OrchestrationStatus.RUNNING

    async def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit event for UI updates via SSE.

        Args:
            event_type: Type of event (track_started, track_stabilized, etc.)
            data: Event payload
        """
        from app.api.v1.routers.production import publish_event

        if not self._state:
            return

        try:
            await publish_event(self._state.project_id, event_type, data)
        except Exception as e:
            logger.warning(f"Failed to emit event {event_type}: {e}")

    async def get_status(self) -> Optional[OrchestrationState]:
        """Get current orchestration state."""
        return self._state
