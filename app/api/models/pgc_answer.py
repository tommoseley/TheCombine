"""PGC Answer model for persisting Pre-Generation Clarification answers.

Per WS-PGC-VALIDATION-001 Phase 2.

Stores PGC answers as first-class documents with full provenance for:
- Audit trail of what was answered
- QA validation against source answers
- Future analytics on question effectiveness
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class PGCAnswer(Base):
    """Stores PGC (Pre-Generation Clarification) answers.

    Links workflow execution, project, and the specific PGC node
    to enable full traceability of clarification responses.
    """

    __tablename__ = "pgc_answers"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Links to workflow execution
    execution_id = Column(String(36), nullable=False, index=True)
    workflow_id = Column(String(100), nullable=False)

    # Links to project
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)

    # The node that generated the questions
    pgc_node_id = Column(String(100), nullable=False)

    # Schema reference for validation
    schema_ref = Column(String(255), nullable=False)

    # The questions that were asked (snapshot at time of answer)
    questions = Column(JSONB, nullable=False)

    # The answers provided by the user
    answers = Column(JSONB, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "project_id": str(self.project_id),
            "pgc_node_id": self.pgc_node_id,
            "schema_ref": self.schema_ref,
            "questions": self.questions,
            "answers": self.answers,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
