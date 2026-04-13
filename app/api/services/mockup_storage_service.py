"""Mockup storage service for project artifact management.

Mediates all artifact storage: validation, thumbnail generation, persistence,
and retrieval of binary artifacts attached to projects.
"""

import base64
import io
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models.project_artifact import ProjectArtifact

logger = logging.getLogger(__name__)

# Default stage hints when none provided
_DEFAULT_STAGE_HINTS = ["project_discovery", "technical_architecture"]


class MockupStorageService:
    """Service for storing and retrieving project artifacts (mockups, PDFs, images)."""

    ALLOWED_MIME_TYPES = {"image/png", "image/jpeg", "application/pdf"}
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
    MAX_PDF_SIZE = 20 * 1024 * 1024    # 20 MB
    THUMBNAIL_MAX_DIM = 256

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def _validate(self, file_content: bytes, mime_type: str) -> None:
        """Validate mime type and file size. Raises ValueError on failure."""
        if mime_type not in self.ALLOWED_MIME_TYPES:
            raise ValueError(
                f"Unsupported mime type '{mime_type}'. "
                f"Allowed: {', '.join(sorted(self.ALLOWED_MIME_TYPES))}"
            )

        size = len(file_content)
        if mime_type == "application/pdf":
            if size > self.MAX_PDF_SIZE:
                raise ValueError(
                    f"PDF too large ({size} bytes). Maximum: {self.MAX_PDF_SIZE} bytes"
                )
        else:
            if size > self.MAX_IMAGE_SIZE:
                raise ValueError(
                    f"Image too large ({size} bytes). Maximum: {self.MAX_IMAGE_SIZE} bytes"
                )

    # ------------------------------------------------------------------
    # Thumbnail generation
    # ------------------------------------------------------------------

    def _generate_thumbnail(self, file_content: bytes, mime_type: str) -> bytes | None:
        """Generate JPEG thumbnail for image types. Returns None for PDFs."""
        if mime_type == "application/pdf":
            return None

        try:
            from PIL import Image

            img = Image.open(io.BytesIO(file_content))
            img.thumbnail((self.THUMBNAIL_MAX_DIM, self.THUMBNAIL_MAX_DIM))

            # Convert to RGB if necessary (e.g., RGBA PNGs)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=80)
            return buf.getvalue()
        except Exception:
            logger.warning("Failed to generate thumbnail", exc_info=True)
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def save(
        self,
        project_id: UUID,
        file_content: bytes,
        mime_type: str,
        label: str,
        uploaded_by: str | None = None,
        stage_hints: list[str] | None = None,
    ) -> ProjectArtifact:
        """Validate, generate thumbnail, persist to DB. Returns ORM instance."""
        self._validate(file_content, mime_type)

        thumbnail = self._generate_thumbnail(file_content, mime_type)
        hints = stage_hints if stage_hints is not None else list(_DEFAULT_STAGE_HINTS)

        artifact = ProjectArtifact(
            project_id=project_id,
            label=label,
            artifact_type="mockup",
            mime_type=mime_type,
            file_size_bytes=len(file_content),
            file_content=file_content,
            thumbnail_content=thumbnail,
            uploaded_by=uploaded_by,
            metadata_={"stage_hints": hints},
        )
        self.db.add(artifact)
        await self.db.flush()
        return artifact

    async def _get_scoped(self, project_id: UUID, artifact_id: UUID) -> ProjectArtifact:
        """Load artifact scoped to project. Raises ValueError if not found or wrong project."""
        result = await self.db.execute(
            select(ProjectArtifact).where(
                ProjectArtifact.id == artifact_id,
                ProjectArtifact.project_id == project_id,
            )
        )
        artifact = result.scalars().first()
        if artifact is None:
            raise ValueError(f"Artifact {artifact_id} not found in project {project_id}")
        return artifact

    async def load(self, project_id: UUID, artifact_id: UUID) -> tuple[bytes, str]:
        """Return (file_content, mime_type). Raises ValueError if not found."""
        artifact = await self._get_scoped(project_id, artifact_id)
        return artifact.file_content, artifact.mime_type

    async def load_thumbnail(self, project_id: UUID, artifact_id: UUID) -> tuple[bytes, str]:
        """Return (thumbnail_bytes, mime_type). Raises ValueError if not found or no thumbnail."""
        artifact = await self._get_scoped(project_id, artifact_id)
        if artifact.thumbnail_content is None:
            raise ValueError(f"Artifact {artifact_id} has no thumbnail")
        return artifact.thumbnail_content, "image/jpeg"

    async def delete(self, project_id: UUID, artifact_id: UUID) -> None:
        """Delete artifact row. Raises ValueError if not found."""
        artifact = await self._get_scoped(project_id, artifact_id)
        await self.db.delete(artifact)
        await self.db.flush()

    async def list_for_project(self, project_id: UUID) -> list[ProjectArtifact]:
        """List all artifacts for a project, ordered by created_at desc."""
        result = await self.db.execute(
            select(ProjectArtifact)
            .where(ProjectArtifact.project_id == project_id)
            .order_by(ProjectArtifact.created_at.desc())
        )
        return list(result.scalars().all())

    async def load_as_base64(self, project_id: UUID, artifact_id: UUID) -> tuple[str, str]:
        """Return (base64_encoded_content, mime_type) for prompt injection."""
        content, mime_type = await self.load(project_id, artifact_id)
        return base64.b64encode(content).decode("ascii"), mime_type

    async def update(
        self,
        project_id: UUID,
        artifact_id: UUID,
        label: str | None = None,
        stage_hints: list[str] | None = None,
    ) -> ProjectArtifact:
        """Update label and/or stage_hints. Raises ValueError if not found."""
        artifact = await self._get_scoped(project_id, artifact_id)

        if label is not None:
            artifact.label = label
        if stage_hints is not None:
            # Merge with existing metadata
            meta = dict(artifact.metadata_ or {})
            meta["stage_hints"] = stage_hints
            artifact.metadata_ = meta

        await self.db.flush()
        return artifact
