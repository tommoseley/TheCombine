"""
Repository protocol for LLM execution logging.

Key design rules:
- Repository does NOT commit (caller owns transaction)
- DTOs are dataclasses (no ORM dependency)
- UUID for correlation_id everywhere
"""

from typing import Protocol, Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass


# =============================================================================
# DATA TRANSFER OBJECTS
# =============================================================================

@dataclass
class LLMRunRecord:
    """LLM run data."""
    # Required fields (no defaults) must come first
    id: UUID
    correlation_id: UUID
    role: str
    model_provider: str
    model_name: str
    prompt_id: str
    prompt_version: str
    effective_prompt_hash: str
    status: str
    started_at: datetime
    # Optional fields (with defaults)
    project_id: Optional[UUID] = None
    artifact_type: Optional[str] = None
    schema_version: Optional[str] = None
    # ADR-031: Schema Registry tracking
    schema_id: Optional[str] = None
    schema_bundle_hash: Optional[str] = None
    ended_at: Optional[datetime] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost_usd: Optional[Decimal] = None
    primary_error_code: Optional[str] = None
    primary_error_message: Optional[str] = None
    error_count: int = 0
    metadata: Optional[Dict[str, Any]] = None
    workflow_execution_id: Optional[str] = None


@dataclass
class LLMContentRecord:
    """Content storage record."""
    id: UUID
    content_hash: str
    content_text: str
    content_size: int
    created_at: datetime
    accessed_at: datetime


@dataclass
class LLMInputRefRecord:
    """Input reference record."""
    id: UUID
    llm_run_id: UUID
    kind: str
    content_ref: str
    content_hash: str
    content_redacted: bool
    created_at: datetime


@dataclass
class LLMOutputRefRecord:
    """Output reference record."""
    id: UUID
    llm_run_id: UUID
    kind: str
    content_ref: str
    content_hash: str
    parse_status: Optional[str]
    validation_status: Optional[str]
    created_at: datetime


@dataclass
class LLMErrorRecord:
    """Error record."""
    id: UUID
    llm_run_id: UUID
    sequence: int
    stage: str
    severity: str
    error_code: Optional[str]
    message: str
    details: Optional[Dict[str, Any]]
    created_at: datetime


# =============================================================================
# REPOSITORY PROTOCOL
# =============================================================================

class LLMLogRepository(Protocol):
    """
    Repository interface for LLM execution logging.
    
    IMPORTANT: Repository does NOT commit. Caller owns transaction boundaries.
    """
    
    async def get_content_by_hash(self, content_hash: str) -> Optional[LLMContentRecord]:
        ...
    
    async def insert_content(self, record: LLMContentRecord) -> None:
        ...
    
    async def touch_content_accessed(self, content_id: UUID) -> None:
        ...
    
    async def insert_run(self, record: LLMRunRecord) -> None:
        ...
    
    async def update_run_completion(
        self,
        run_id: UUID,
        status: str,
        ended_at: datetime,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        cost_usd: Optional[Decimal] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        ...
    
    async def bump_error_summary(
        self,
        run_id: UUID,
        error_code: Optional[str],
        message: str,
    ) -> None:
        ...
    
    async def get_run(self, run_id: UUID) -> Optional[LLMRunRecord]:
        ...
    
    async def get_run_by_correlation_id(self, correlation_id: UUID) -> Optional[LLMRunRecord]:
        ...
    
    async def insert_input_ref(self, record: LLMInputRefRecord) -> None:
        ...
    
    async def insert_output_ref(self, record: LLMOutputRefRecord) -> None:
        ...
    
    async def get_inputs_for_run(self, run_id: UUID) -> List[LLMInputRefRecord]:
        ...
    
    async def get_outputs_for_run(self, run_id: UUID) -> List[LLMOutputRefRecord]:
        ...
    
    async def get_next_error_sequence(self, run_id: UUID) -> int:
        ...
    
    async def insert_error(self, record: LLMErrorRecord) -> None:
        ...
    
    async def get_errors_for_run(self, run_id: UUID) -> List[LLMErrorRecord]:
        ...
    
    async def commit(self) -> None:
        ...
    
    async def rollback(self) -> None:
        ...
