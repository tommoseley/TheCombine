"""PGC context merging and answer reconciliation.

Extracted from PlanExecutor (WS-CRAP decomposition).
Handles PGC user answer processing, question loading for merge,
and PGC answer loading for QA validation.
"""

import logging
from typing import Any, Optional

from app.domain.workflow.document_workflow_state import DocumentWorkflowState
from app.domain.workflow.nodes.base import DocumentWorkflowContext
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def handle_pgc_user_answers(
    execution_id: str,
    current_node,  # Node
    state: DocumentWorkflowState,
    plan,  # WorkflowPlan
    user_input: Any,
    ops_service,
    operation_executor,
    persistence,
    db_session: Optional[AsyncSession],
    emit_internal_step_fn,
    execute_step_fn,
) -> DocumentWorkflowState:
    """Handle PGC node user answer submission.

    Merges user answers with PGC questions, extracts invariants,
    stores in context_state, then routes to next node.

    Args:
        execution_id: The workflow execution ID
        current_node: The PGC node
        state: Current execution state
        plan: Workflow plan
        user_input: User-provided answers
        ops_service: MechanicalOpsService instance
        persistence: State persistence backend
        db_session: Database session (may be None)
        emit_internal_step_fn: Callback for emitting internal step events
        execute_step_fn: Callback for executing next step

    Returns:
        Updated execution state
    """
    logger.info(
        f"PGC node {current_node.node_id} received user answers "
        f"- merging clarifications (ADR-042)"
    )

    # Emit internal_step for merge phase
    if current_node.internals and "merge" in current_node.internals:
        await emit_internal_step_fn(plan, state, current_node, "merge")

    # ADR-042: Get questions (with DB fallback for restart scenarios)
    questions = await get_pgc_questions_for_merge(state, db_session)

    # ADR-042/ADR-047: Merge questions with answers via mechanical operation
    op = ops_service.get_operation("pgc_clarification_processor") if ops_service else None
    if op and operation_executor:
        result = await operation_executor.execute(
            operation=op,
            inputs={"questions": questions, "answers": user_input},
        )
        if result.success:
            clarifications = result.output.get("clarifications", [])
            invariants = result.output.get("invariants", [])
        else:
            logger.warning(
                f"Clarification merge failed: {result.error}, using fallback"
            )
            from app.domain.workflow.clarification_merger import (
                merge_clarifications,
                extract_invariants,
            )
            clarifications = merge_clarifications(questions, user_input)
            invariants = extract_invariants(clarifications)
    else:
        from app.domain.workflow.clarification_merger import (
            merge_clarifications,
            extract_invariants,
        )
        clarifications = merge_clarifications(questions, user_input)
        invariants = extract_invariants(clarifications)

    state.update_context_state({
        "pgc_answers": user_input,
        "pgc_clarifications": clarifications,
        "pgc_invariants": invariants,
    })

    logger.info(
        f"ADR-042: Merged {len(clarifications)} clarifications, "
        f"{len(invariants)} binding invariants"
    )

    # Route to next node using "success" outcome
    from app.domain.workflow.edge_router import EdgeRouter
    from app.domain.workflow.plan_executor import PlanExecutorError

    router = EdgeRouter(plan)
    next_node_id, edge = router.get_next_node(
        current_node_id=current_node.node_id,
        outcome="success",
        state=state,
    )
    if next_node_id:
        state.current_node_id = next_node_id
        from app.domain.workflow.document_workflow_state import DocumentWorkflowStatus
        state.status = DocumentWorkflowStatus.RUNNING
        await persistence.save(state)
        return await execute_step_fn(execution_id)
    else:
        raise PlanExecutorError(
            f"No edge from PGC node {current_node.node_id} with outcome 'success'"
        )


async def get_pgc_questions_for_merge(
    state: DocumentWorkflowState,
    db_session: Optional[AsyncSession],
) -> list:
    """Get PGC questions for merging with answers (ADR-042).

    Questions come from state.pending_user_input_payload first,
    with DB fallback for restart scenarios.

    Args:
        state: Current execution state
        db_session: Database session (may be None)

    Returns:
        List of PGC question objects
    """
    # Try in-memory first (normal case)
    if state.pending_user_input_payload:
        questions = state.pending_user_input_payload.get("questions", [])
        if questions:
            logger.debug(f"ADR-042: Got {len(questions)} questions from pending payload")
            return questions

    # Fallback: load from DB (handles restart scenario)
    if db_session:
        try:
            from app.domain.repositories.pgc_answer_repository import PGCAnswerRepository

            repo = PGCAnswerRepository(db_session)
            pgc_record = await repo.get_by_execution(state.execution_id)
            if pgc_record and pgc_record.questions:
                logger.info(
                    f"ADR-042: Loaded {len(pgc_record.questions)} questions from DB fallback"
                )
                return pgc_record.questions
        except Exception as e:
            logger.warning(f"ADR-042: Failed to load questions from DB: {e}")

    logger.warning("ADR-042: No questions available for merge")
    return []


async def load_pgc_answers_for_qa(
    state: DocumentWorkflowState,
    context: DocumentWorkflowContext,
    db_session: Optional[AsyncSession],
    ops_service=None,
    operation_executor=None,
) -> None:
    """Load PGC answers for QA validation.

    ADR-064 resolution order:
    1. If authority already hydrated (authority_source=durable_store), skip
    2. Try durable authority store (ADR-064)
    3. Fall back to execution-scoped pgc_answers table (ADR-042)

    Args:
        state: Current execution state
        context: Execution context to update
        db_session: Database session (may be None)
        ops_service: MechanicalOpsService for clarification merge
    """
    # Already hydrated from authority store (WS-AUTH-005)
    if context.context_state.get("authority_source") == "durable_store":
        logger.debug("ADR-064: Authority already hydrated from durable store, skipping")
        return

    # Check if clarifications already in context (normal flow)
    if context.context_state.get("pgc_clarifications"):
        logger.debug("ADR-042: Clarifications already in context, skipping DB load")
        return

    if not db_session:
        return

    # ADR-064: Try durable authority store first
    authority_loaded = False
    try:
        from app.domain.repositories.authority_repository import PostgresAuthorityRepository
        from app.domain.services.authority_service import AuthorityService
        from uuid import UUID

        auth_repo = PostgresAuthorityRepository(db_session)
        auth_service = AuthorityService(auth_repo)
        try:
            project_id = UUID(state.project_id) if isinstance(state.project_id, str) else state.project_id
        except (ValueError, AttributeError):
            logger.debug(f"ADR-064: project_id '{state.project_id}' is not a valid UUID, skipping authority load")
            raise  # fall through to outer except -> execution-scoped fallback

        bundle = await auth_service.get_authority_bundle(project_id)

        if bundle["authority_source"] == "durable_store":
            context.context_state["pgc_answers"] = bundle["pgc_answers"]
            context.context_state["pgc_questions"] = bundle["pgc_questions"]
            context.context_state["authority_record_ids"] = bundle["authority_record_ids"]
            context.context_state["authority_source"] = "durable_store"
            authority_loaded = True
            logger.info(
                f"ADR-064: Loaded {len(bundle['pgc_answers'])} authority records "
                f"from durable store for project {state.project_id}",
                extra={"authority_record_ids": [str(rid) for rid in bundle["authority_record_ids"]]},
            )
    except Exception as e:
        logger.warning(f"ADR-064: Durable authority load failed, falling back: {e}")

    # Fall back to execution-scoped pgc_answers table
    if not authority_loaded:
        try:
            from app.domain.repositories.pgc_answer_repository import PGCAnswerRepository

            repo = PGCAnswerRepository(db_session)
            pgc_answer = await repo.get_by_execution(state.execution_id)

            if pgc_answer:
                context.context_state["pgc_questions"] = pgc_answer.questions
                context.context_state["pgc_answers"] = pgc_answer.answers
                context.context_state["authority_source"] = "execution_scoped"

                logger.info(
                    f"Loaded PGC answers for QA validation (execution-scoped): "
                    f"{len(pgc_answer.questions)} questions"
                )
            else:
                context.context_state["authority_source"] = "none"
                logger.debug(
                    f"No PGC answers found for execution {state.execution_id}"
                )
        except Exception as e:
            context.context_state["authority_source"] = "none"
            logger.warning(f"Failed to load PGC answers for QA: {e}")

    # ADR-042/ADR-047: Merge clarifications if answers loaded but clarifications not
    pgc_answers_dict = context.context_state.get("pgc_answers")
    pgc_questions_list = context.context_state.get("pgc_questions")
    if pgc_answers_dict and pgc_questions_list and not context.context_state.get("pgc_clarifications"):
        try:
            op = ops_service.get_operation("pgc_clarification_processor") if ops_service else None
            if op and operation_executor:
                result = await operation_executor.execute(
                    operation=op,
                    inputs={"questions": pgc_questions_list, "answers": pgc_answers_dict},
                )
                if result.success:
                    clarifications = result.output.get("clarifications", [])
                    invariants = result.output.get("invariants", [])
                else:
                    logger.warning(f"Clarification merge failed: {result.error}, using fallback")
                    from app.domain.workflow.clarification_merger import merge_clarifications, extract_invariants
                    clarifications = merge_clarifications(pgc_questions_list, pgc_answers_dict)
                    invariants = extract_invariants(clarifications)
            else:
                from app.domain.workflow.clarification_merger import merge_clarifications, extract_invariants
                clarifications = merge_clarifications(pgc_questions_list, pgc_answers_dict)
                invariants = extract_invariants(clarifications)

            context.context_state["pgc_clarifications"] = clarifications
            context.context_state["pgc_invariants"] = invariants

            logger.info(
                f"ADR-042: Merged {len(clarifications)} clarifications "
                f"({len(invariants)} binding) for QA"
            )
        except Exception as e:
            logger.warning(f"ADR-042: Clarification merge failed: {e}")
