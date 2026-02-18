"""
Fan-out services for progressive backlog expansion.

EpicFeatureFanoutService: Generate FEATURE backlog_items for an Epic.
FeatureStoryFanoutService: Generate STORY backlog_items for Features under an Epic.

Both services execute DCWs through PlanExecutor per DD-BCP-005-01,
then apply post-DCW mechanical validation and reconciliation.

WS-BCP-005.
"""

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.domain.services.graph_validator import validate_backlog
from app.domain.services.set_reconciler import reconcile, ReconciliationResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class FanoutResult:
    """Result of a fan-out expansion run."""
    status: str              # "completed" | "needs_confirmation" | "failed"
    run_id: str
    source_id: str           # Epic or feature ID that was expanded
    source_type: str         # "epic" | "feature"
    items: List[Dict[str, Any]] = field(default_factory=list)

    # Reconciliation (populated on re-runs when existing items exist)
    reconciliation: Optional[ReconciliationResult] = None

    # Validation
    validation_errors: Optional[Dict[str, Any]] = None

    # Metadata for staleness detection
    source_hash: Optional[str] = None
    execution_id: Optional[str] = None
    document_id: Optional[str] = None

    errors: Optional[Dict[str, Any]] = None

    @property
    def has_drops(self) -> bool:
        """True if reconciliation found items to drop (needs UI confirmation)."""
        return self.reconciliation is not None and self.reconciliation.has_drops


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    """UTC timestamp as ISO string."""
    return datetime.now(timezone.utc).isoformat()


def _compute_structural_hash(item: dict) -> str:
    """Compute structural hash from base fields only (hash boundary invariant)."""
    base = {
        "id": item.get("id"),
        "level": item.get("level"),
        "parent_id": item.get("parent_id"),
        "depends_on": sorted(item.get("depends_on", [])),
        "priority_score": item.get("priority_score"),
    }
    canonical = json.dumps(base, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# EpicFeatureFanoutService
# ---------------------------------------------------------------------------

class EpicFeatureFanoutService:
    """
    Generate FEATURE-level backlog_items for a single Epic.

    Sequence:
    1. Load epic and context from DB
    2. Build sibling epic boundary summary
    3. Run feature_set_generator DCW via PlanExecutor
    4. Validate produced features (schema, hierarchy, dependency)
    5. Reconcile with existing features (if re-run)
    6. Return result (with reconciliation if drops exist)

    Dependencies injected for testability.
    """

    def __init__(self, db_session, plan_executor):
        self._db = db_session
        self._executor = plan_executor

    async def run(
        self,
        project_id: str,
        epic_id: str,
    ) -> FanoutResult:
        """Generate features for a single epic.

        Args:
            project_id: Project UUID
            epic_id: The epic's backlog item ID (e.g., "E001")

        Returns:
            FanoutResult with generated features and reconciliation info.
        """
        run_id = f"run-{uuid.uuid4().hex[:12]}"

        # Step 1: Load the target epic
        epic_item = await self._load_backlog_item(project_id, epic_id)
        if epic_item is None:
            return FanoutResult(
                status="failed",
                run_id=run_id,
                source_id=epic_id,
                source_type="epic",
                errors={"error": "epic_not_found", "detail": f"Epic {epic_id} not found"},
            )

        source_hash = _compute_structural_hash(epic_item)

        # Step 2: Build sibling epic boundary summary
        all_epics = await self._load_backlog_items_by_level(project_id, "EPIC")
        sibling_summary = [
            {
                "epic_id": e["id"],
                "title": e.get("title", ""),
                "scope_summary": _extract_scope_summary(e),
            }
            for e in all_epics
            if e["id"] != epic_id
        ]

        # Step 3: Load intent summary
        intent_summary = await self._load_intent_summary(project_id)

        # Step 4: Run feature_set_generator DCW
        input_documents = {
            "epic_backlog_item": epic_item,
            "sibling_epic_boundary_summary": sibling_summary,
            "intent_summary": intent_summary or {},
        }

        # Add architecture summary if available
        arch_summary = await self._load_architecture_summary(project_id)
        if arch_summary:
            input_documents["architecture_summary"] = arch_summary

        dcw_result = await self._run_dcw(
            project_id=project_id,
            document_type="feature_set_generator",
            input_documents=input_documents,
        )

        if dcw_result["terminal_outcome"] != "stabilized":
            return FanoutResult(
                status="failed",
                run_id=run_id,
                source_id=epic_id,
                source_type="epic",
                source_hash=source_hash,
                execution_id=dcw_result.get("execution_id"),
                errors={"error": "generation_failed", "detail": "Feature set generator DCW failed"},
            )

        # Step 5: Extract produced feature items
        produced_content = await self._load_latest_document(project_id, "feature_set_generator")
        if not produced_content or "items" not in produced_content:
            return FanoutResult(
                status="failed",
                run_id=run_id,
                source_id=epic_id,
                source_type="epic",
                source_hash=source_hash,
                execution_id=dcw_result.get("execution_id"),
                errors={"error": "no_items_produced", "detail": "DCW produced no feature items"},
            )

        candidate_items = produced_content["items"]

        # Step 6: Validate features (post-DCW mechanical validation)
        # Include parent epic in validation set so hierarchy validator
        # can verify parent_id references correctly.
        validation_set = [epic_item] + candidate_items
        validation = validate_backlog(validation_set)
        if not validation.valid:
            return FanoutResult(
                status="failed",
                run_id=run_id,
                source_id=epic_id,
                source_type="epic",
                source_hash=source_hash,
                execution_id=dcw_result.get("execution_id"),
                items=candidate_items,
                validation_errors={
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
                errors={"error": "validation_failed"},
            )

        # Step 7: Reconcile with existing features (if any)
        existing_features = await self._load_backlog_items_by_parent(project_id, epic_id)
        recon_result = reconcile(existing_features, candidate_items)

        if recon_result.has_drops:
            # Drops exist — return for UI confirmation before applying
            return FanoutResult(
                status="needs_confirmation",
                run_id=run_id,
                source_id=epic_id,
                source_type="epic",
                items=candidate_items,
                reconciliation=recon_result,
                source_hash=source_hash,
                execution_id=dcw_result.get("execution_id"),
                document_id=dcw_result.get("document_id"),
            )

        # No drops — auto-apply
        return FanoutResult(
            status="completed",
            run_id=run_id,
            source_id=epic_id,
            source_type="epic",
            items=candidate_items,
            reconciliation=recon_result,
            source_hash=source_hash,
            execution_id=dcw_result.get("execution_id"),
            document_id=dcw_result.get("document_id"),
        )

    # -------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------

    async def _load_backlog_item(self, project_id: str, item_id: str) -> Optional[dict]:
        """Load a single backlog_item by instance_id."""
        from sqlalchemy import select
        from app.api.models.document import Document
        from uuid import UUID

        result = await self._db.execute(
            select(Document).where(
                Document.space_id == UUID(project_id),
                Document.doc_type_id == "backlog_item",
                Document.instance_id == item_id,
                Document.is_latest == True,  # noqa: E712 — SQLAlchemy column compare
            )
        )
        doc = result.scalar_one_or_none()
        return doc.content if doc else None

    async def _load_backlog_items_by_level(
        self, project_id: str, level: str
    ) -> List[dict]:
        """Load all backlog_items of a given level."""
        from sqlalchemy import select
        from app.api.models.document import Document
        from uuid import UUID

        result = await self._db.execute(
            select(Document).where(
                Document.space_id == UUID(project_id),
                Document.doc_type_id == "backlog_item",
                Document.is_latest == True,  # noqa: E712 — SQLAlchemy column compare
            )
        )
        docs = result.scalars().all()
        return [
            d.content for d in docs
            if d.content and d.content.get("level") == level
        ]

    async def _load_backlog_items_by_parent(
        self, project_id: str, parent_id: str
    ) -> List[dict]:
        """Load all backlog_items with a given parent_id."""
        from sqlalchemy import select
        from app.api.models.document import Document
        from uuid import UUID

        result = await self._db.execute(
            select(Document).where(
                Document.space_id == UUID(project_id),
                Document.doc_type_id == "backlog_item",
                Document.is_latest == True,  # noqa: E712 — SQLAlchemy column compare
            )
        )
        docs = result.scalars().all()
        return [
            d.content for d in docs
            if d.content and d.content.get("parent_id") == parent_id
        ]

    async def _load_intent_summary(self, project_id: str) -> Optional[dict]:
        """Load the latest intent_packet for context."""
        return await self._load_latest_document(project_id, "intent_packet")

    async def _load_architecture_summary(self, project_id: str) -> Optional[dict]:
        """Load the latest technical_architecture for context."""
        return await self._load_latest_document(project_id, "technical_architecture")

    async def _load_latest_document(
        self, project_id: str, doc_type_id: str
    ) -> Optional[dict]:
        """Load the latest document of a given type."""
        from sqlalchemy import select
        from app.api.models.document import Document
        from uuid import UUID

        result = await self._db.execute(
            select(Document).where(
                Document.space_id == UUID(project_id),
                Document.doc_type_id == doc_type_id,
                Document.is_latest == True,  # noqa: E712 — SQLAlchemy column compare
            )
        )
        doc = result.scalar_one_or_none()
        return doc.content if doc else None

    async def _run_dcw(
        self,
        project_id: str,
        document_type: str,
        input_documents: dict,
    ) -> dict:
        """Run a DCW to completion via PlanExecutor.

        Returns dict with terminal_outcome, execution_id, document_id.
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

        document_id = None
        if terminal_outcome == "stabilized":
            from sqlalchemy import select
            from app.api.models.document import Document
            from uuid import UUID
            result = await self._db.execute(
                select(Document.id).where(
                    Document.space_id == UUID(project_id),
                    Document.doc_type_id == document_type,
                    Document.is_latest == True,  # noqa: E712 — SQLAlchemy column compare
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


# ---------------------------------------------------------------------------
# FeatureStoryFanoutService
# ---------------------------------------------------------------------------

class FeatureStoryFanoutService:
    """
    Generate STORY-level backlog_items for Features under a single Epic.

    Scope:
    - Per epic: generates stories for all features under that epic
    - Per feature: generates stories for a single feature

    Sequence:
    1. Load target feature(s) and parent epic from DB
    2. Load existing stories (for re-run reconciliation context)
    3. Run story_set_generator DCW via PlanExecutor
    4. Validate produced stories (schema, hierarchy, dependency)
    5. Reconcile with existing stories (if re-run)
    6. Return result (with reconciliation if drops exist)
    """

    def __init__(self, db_session, plan_executor):
        self._db = db_session
        self._executor = plan_executor

    async def run(
        self,
        project_id: str,
        epic_id: str,
        feature_id: Optional[str] = None,
    ) -> FanoutResult:
        """Generate stories for features under an epic.

        Args:
            project_id: Project UUID
            epic_id: Parent epic's backlog item ID (e.g., "E001")
            feature_id: Optional specific feature ID. If None, generates for all features.

        Returns:
            FanoutResult with generated stories and reconciliation info.
        """
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        source_id = feature_id or epic_id
        source_type = "feature" if feature_id else "epic"

        # Step 1: Load parent epic
        epic_item = await self._load_backlog_item(project_id, epic_id)
        if epic_item is None:
            return FanoutResult(
                status="failed",
                run_id=run_id,
                source_id=source_id,
                source_type=source_type,
                errors={"error": "epic_not_found", "detail": f"Epic {epic_id} not found"},
            )

        # Step 2: Load target feature(s)
        if feature_id:
            feature_item = await self._load_backlog_item(project_id, feature_id)
            if feature_item is None:
                return FanoutResult(
                    status="failed",
                    run_id=run_id,
                    source_id=source_id,
                    source_type=source_type,
                    errors={"error": "feature_not_found", "detail": f"Feature {feature_id} not found"},
                )
            target_features = [feature_item]
        else:
            target_features = await self._load_backlog_items_by_parent(project_id, epic_id)
            if not target_features:
                return FanoutResult(
                    status="failed",
                    run_id=run_id,
                    source_id=source_id,
                    source_type=source_type,
                    errors={"error": "no_features", "detail": f"No features found under epic {epic_id}"},
                )

        # Compute source_hash from the features being expanded
        source_hash = _compute_source_hash_for_features(target_features)

        # Step 3: Load existing stories for re-run context
        existing_stories = []
        for feature in target_features:
            fid = feature["id"]
            stories = await self._load_backlog_items_by_parent(project_id, fid)
            existing_stories.extend(stories)

        existing_story_titles = [
            {"id": s["id"], "title": s.get("title", "")}
            for s in existing_stories
        ]

        # Step 4: Run story_set_generator DCW
        input_documents = {
            "feature_backlog_items": target_features,
            "parent_epic_summary": {
                "id": epic_item["id"],
                "title": epic_item.get("title", ""),
                "summary": epic_item.get("summary", ""),
            },
            "intent_summary": await self._load_intent_summary(project_id) or {},
        }

        if existing_story_titles:
            input_documents["existing_sibling_story_titles"] = existing_story_titles

        arch_summary = await self._load_architecture_summary(project_id)
        if arch_summary:
            input_documents["architecture_summary"] = arch_summary

        dcw_result = await self._run_dcw(
            project_id=project_id,
            document_type="story_set_generator",
            input_documents=input_documents,
        )

        if dcw_result["terminal_outcome"] != "stabilized":
            return FanoutResult(
                status="failed",
                run_id=run_id,
                source_id=source_id,
                source_type=source_type,
                source_hash=source_hash,
                execution_id=dcw_result.get("execution_id"),
                errors={"error": "generation_failed", "detail": "Story set generator DCW failed"},
            )

        # Step 5: Extract produced story items
        produced_content = await self._load_latest_document(project_id, "story_set_generator")
        if not produced_content or "items" not in produced_content:
            return FanoutResult(
                status="failed",
                run_id=run_id,
                source_id=source_id,
                source_type=source_type,
                source_hash=source_hash,
                execution_id=dcw_result.get("execution_id"),
                errors={"error": "no_items_produced", "detail": "DCW produced no story items"},
            )

        candidate_items = produced_content["items"]

        # Step 6: Validate stories (post-DCW mechanical validation)
        # Include parent features and grandparent epic in validation set
        # so hierarchy validator can verify parent_id references correctly.
        validation_set = [epic_item] + target_features + candidate_items
        validation = validate_backlog(validation_set)
        if not validation.valid:
            return FanoutResult(
                status="failed",
                run_id=run_id,
                source_id=source_id,
                source_type=source_type,
                source_hash=source_hash,
                execution_id=dcw_result.get("execution_id"),
                items=candidate_items,
                validation_errors={
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
                errors={"error": "validation_failed"},
            )

        # Step 7: Reconcile with existing stories
        recon_result = reconcile(existing_stories, candidate_items)

        if recon_result.has_drops:
            return FanoutResult(
                status="needs_confirmation",
                run_id=run_id,
                source_id=source_id,
                source_type=source_type,
                items=candidate_items,
                reconciliation=recon_result,
                source_hash=source_hash,
                execution_id=dcw_result.get("execution_id"),
                document_id=dcw_result.get("document_id"),
            )

        return FanoutResult(
            status="completed",
            run_id=run_id,
            source_id=source_id,
            source_type=source_type,
            items=candidate_items,
            reconciliation=recon_result,
            source_hash=source_hash,
            execution_id=dcw_result.get("execution_id"),
            document_id=dcw_result.get("document_id"),
        )

    # -------------------------------------------------------------------
    # Internal helpers (same patterns as EpicFeatureFanoutService)
    # -------------------------------------------------------------------

    async def _load_backlog_item(self, project_id: str, item_id: str) -> Optional[dict]:
        """Load a single backlog_item by instance_id."""
        from sqlalchemy import select
        from app.api.models.document import Document
        from uuid import UUID

        result = await self._db.execute(
            select(Document).where(
                Document.space_id == UUID(project_id),
                Document.doc_type_id == "backlog_item",
                Document.instance_id == item_id,
                Document.is_latest == True,  # noqa: E712 — SQLAlchemy column compare
            )
        )
        doc = result.scalar_one_or_none()
        return doc.content if doc else None

    async def _load_backlog_items_by_parent(
        self, project_id: str, parent_id: str
    ) -> List[dict]:
        """Load all backlog_items with a given parent_id."""
        from sqlalchemy import select
        from app.api.models.document import Document
        from uuid import UUID

        result = await self._db.execute(
            select(Document).where(
                Document.space_id == UUID(project_id),
                Document.doc_type_id == "backlog_item",
                Document.is_latest == True,  # noqa: E712 — SQLAlchemy column compare
            )
        )
        docs = result.scalars().all()
        return [
            d.content for d in docs
            if d.content and d.content.get("parent_id") == parent_id
        ]

    async def _load_intent_summary(self, project_id: str) -> Optional[dict]:
        """Load the latest intent_packet for context."""
        return await self._load_latest_document(project_id, "intent_packet")

    async def _load_architecture_summary(self, project_id: str) -> Optional[dict]:
        """Load the latest technical_architecture for context."""
        return await self._load_latest_document(project_id, "technical_architecture")

    async def _load_latest_document(
        self, project_id: str, doc_type_id: str
    ) -> Optional[dict]:
        """Load the latest document of a given type."""
        from sqlalchemy import select
        from app.api.models.document import Document
        from uuid import UUID

        result = await self._db.execute(
            select(Document).where(
                Document.space_id == UUID(project_id),
                Document.doc_type_id == doc_type_id,
                Document.is_latest == True,  # noqa: E712 — SQLAlchemy column compare
            )
        )
        doc = result.scalar_one_or_none()
        return doc.content if doc else None

    async def _run_dcw(
        self,
        project_id: str,
        document_type: str,
        input_documents: dict,
    ) -> dict:
        """Run a DCW to completion via PlanExecutor."""
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

        document_id = None
        if terminal_outcome == "stabilized":
            from sqlalchemy import select
            from app.api.models.document import Document
            from uuid import UUID
            result = await self._db.execute(
                select(Document.id).where(
                    Document.space_id == UUID(project_id),
                    Document.doc_type_id == document_type,
                    Document.is_latest == True,  # noqa: E712 — SQLAlchemy column compare
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


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _extract_scope_summary(epic: dict) -> str:
    """Extract a one-line scope summary from an epic's details."""
    details = epic.get("details", {})
    scope = details.get("scope", [])
    if scope:
        return scope[0] if len(scope) == 1 else "; ".join(scope[:2])
    return epic.get("summary", "")


def _compute_source_hash_for_features(features: List[dict]) -> str:
    """Compute a combined structural hash for a set of features.

    Used as source_hash when generating stories for multiple features.
    """
    hashes = sorted(_compute_structural_hash(f) for f in features)
    combined = "|".join(hashes)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()
