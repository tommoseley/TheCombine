# app/workforce/workforce_api.py

from fastapi import APIRouter, HTTPException, Header
from .workforce_git import write_files, commit_and_push
from .workforce_models import FileChange, CommitRequest, CommitResponse

router = APIRouter(prefix="/workforce", tags=["workforce"])

@router.post("/commit", response_model=CommitResponse)
def workforce_commit(
    req: CommitRequest,
    x_workforce_key: str | None = Header(default=None),
):
    if x_workforce_key != "super-secret":
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not req.changes:
        raise HTTPException(status_code=400, detail="No changes provided")

    write_files([c.model_dump() for c in req.changes])
    commit_hash = commit_and_push(req.message)

    return CommitResponse(status="ok", commit_hash=commit_hash)
