# app/workforce/workforce_models.py

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class FileChange(BaseModel):
    """
    A single file mutation the Workforce wants to apply.
    """
    path: str = Field(
        ...,
        description="Path inside the repo, e.g. 'app/workforce/workforce_api.py'",
    )
    content: str = Field(
        ...,
        description="Full file contents after the change (overwrite semantics).",
    )
    # Optional: later you can support different modes like 'append', 'patch', etc.
    mode: Literal["overwrite"] = Field(
        "overwrite",
        description="How to apply the change. Currently only 'overwrite' is supported.",
    )


class CommitRequest(BaseModel):
    """
    Request body for /workforce/commit.
    """
    message: str = Field(
        ...,
        description="Git commit message to use for this set of changes.",
    )
    changes: List[FileChange] = Field(
        ...,
        description="List of file changes to apply in this commit.",
    )

    # Optional metadata you can start using later if you want:
    author_tag: Optional[str] = Field(
        None,
        description="Logical Workforce author (e.g. 'spec-writer', 'qa-agent').",
    )
    work_item_id: Optional[str] = Field(
        None,
        description="Optional link back to a ticket / story / task id.",
    )


class CommitResponse(BaseModel):
    """
    Response body from /workforce/commit.
    """
    status: str = Field(..., description="Result status, e.g. 'ok'.")
    commit_hash: Optional[str] = Field(
        None,
        description="Git commit hash if a commit was created.",
    )
    details: Optional[str] = Field(
        None,
        description="Any extra info, warnings, etc.",
    )
