"""
Repository protocol for WS execution metrics (WS-METRICS-001).

Key design rules (follows LLM logging pattern):
- Repository does NOT commit (caller owns transaction)
- DTOs are dataclasses (no ORM dependency)
- UUID for all primary keys
"""

from typing import Protocol, Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass


# =============================================================================
# PINNED ENUMS
# =============================================================================

VALID_STATUSES = {"STARTED", "COMPLETED", "FAILED", "HARD_STOP", "BLOCKED"}
VALID_PHASE_NAMES = {"failing_tests", "implement", "verify", "do_no_harm_audit"}


# =============================================================================
# DATA TRANSFER OBJECTS
# =============================================================================

@dataclass
class WSExecutionRecord:
    """WS execution data."""
    # Required fields
    id: UUID
    ws_id: str
    executor: str
    status: str
    started_at: datetime
    # Optional fields
    wp_id: Optional[str] = None
    scope_id: Optional[str] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    phase_metrics: Optional[Dict[str, Any]] = None
    test_metrics: Optional[Dict[str, Any]] = None
    file_metrics: Optional[Dict[str, Any]] = None
    rework_cycles: int = 0
    llm_calls: int = 0
    llm_tokens_in: int = 0
    llm_tokens_out: int = 0
    llm_cost_usd: Optional[Decimal] = None
    created_at: Optional[datetime] = None


@dataclass
class WSBugFixRecord:
    """Bug fix record linked to WS execution."""
    # Required fields
    id: UUID
    ws_execution_id: UUID
    description: str
    root_cause: str
    test_name: str
    fix_summary: str
    autonomous: bool
    # Optional fields
    scope_id: Optional[str] = None
    files_modified: Optional[List[str]] = None
    created_at: Optional[datetime] = None


# =============================================================================
# REPOSITORY PROTOCOL
# =============================================================================

class WSMetricsRepository(Protocol):
    """
    Repository interface for WS execution metrics.

    IMPORTANT: Repository does NOT commit. Caller owns transaction boundaries.
    """

    async def insert_execution(self, record: WSExecutionRecord) -> None:
        ...

    async def get_execution(self, execution_id: UUID) -> Optional[WSExecutionRecord]:
        ...

    async def update_execution(self, execution_id: UUID, **fields) -> None:
        ...

    async def list_executions(
        self,
        wp_id: Optional[str] = None,
        status: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> List[WSExecutionRecord]:
        ...

    async def insert_bug_fix(self, record: WSBugFixRecord) -> None:
        ...

    async def get_bug_fixes_for_execution(self, execution_id: UUID) -> List[WSBugFixRecord]:
        ...

    async def list_bug_fixes(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> List[WSBugFixRecord]:
        ...

    async def commit(self) -> None:
        ...

    async def rollback(self) -> None:
        ...
