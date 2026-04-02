"""
Project Artifact Model — Binary attachments (mockups, reference files) for projects.

Per ADR-068: Project-scoped mockup attachments stored as bytea in PostgreSQL.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index, LargeBinary
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped
from sqlalchemy.sql import func

from app.core.database import Base


class ProjectArtifact(Base):
    """Project-scoped binary artifact (mockup, reference file)."""

    __tablename__ = "project_artifacts"

    id: Mapped[UUID] = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    project_id: Mapped[UUID] = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    label: Mapped[str] = Column(String(255), nullable=False)
    artifact_type: Mapped[str] = Column(String(50), nullable=False, server_default="mockup")
    mime_type: Mapped[str] = Column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = Column(Integer, nullable=False)

    file_content: Mapped[bytes] = Column(LargeBinary, nullable=False)
    thumbnail_content: Mapped[bytes] = Column(LargeBinary, nullable=True)

    uploaded_by: Mapped[str] = Column(String(100), nullable=True)
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    metadata_: Mapped[dict] = Column("metadata", JSONB, nullable=True)

    __table_args__ = (
        Index("ix_project_artifacts_type", "artifact_type"),
    )

    def to_dict(self) -> dict:
        """Return metadata dict (excludes binary content)."""
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "label": self.label,
            "artifact_type": self.artifact_type,
            "mime_type": self.mime_type,
            "file_size_bytes": self.file_size_bytes,
            "uploaded_by": self.uploaded_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.metadata_,
        }
