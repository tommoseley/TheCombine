from fastapi import FastAPI, Request, Form, Depends, HTTPException, status, Response, Header
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from uuid import uuid4
from datetime import datetime

from sqlalchemy import create_engine, Column, String, Text, ForeignKey, Boolean, Integer, select, JSON

from sqlalchemy.orm import sessionmaker, declarative_base, Session, relationship

from pipeline import PipelineStateMachine, PipelineStage, InvalidPipelineTransition

from typing import List, Optional

app = FastAPI()

templates = Jinja2Templates(directory="templates")

# -------------------------------------------------------------------
# Database setup (SQLite + SQLAlchemy)
# -------------------------------------------------------------------

SQLALCHEMY_DATABASE_URL = "sqlite:///./workbench.db"

# check_same_thread=False is required for SQLite with FastAPI
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="active")
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)


class PipelineState(Base):
    __tablename__ = "pipeline_state"

    id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String, nullable=False, index=True)
    stage = Column(String, nullable=False, default="not_started")
    approved = Column (Boolean, nullable=False)
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)

class PipelineActionLog(Base):
    __tablename__ = "pipeline_action_logs"

    id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"), index=True, nullable=False)
    action = Column(String, nullable=False)          # e.g. "start_pm_flow"
    from_stage = Column(String, nullable=True)       # e.g. "not_started"
    to_stage = Column(String, nullable=True)         # e.g. "pm_questions"
    notes = Column(Text, nullable=True)              # optional freeform notes
    created_at = Column(String, nullable=False)      # ISO timestamp

class CanonicalDocument(Base):
    __tablename__ = "canonical_documents"
    id = Column(String, primary_key=True, index=True)
    workspace_id = Column(String, nullable=False, index=True)
    doc_type = Column(String, nullable=False)        # epic | architecture | backlog | pm_questions | ...
    status = Column(String, nullable=False)          # draft | approved | superseded
    schema_version = Column(String, nullable=False)  # e.g. "1"
    content = Column(JSON, nullable=False)           # the validated canonical JSON
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)

# Create tables on startup (simple for MVP)
Base.metadata.create_all(bind=engine)


# Dependency to get a DB session per request
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def log_pipeline_action(
    db: Session,
    *,
    workspace_id: str,
    action: str,
    from_stage: str | None = None,
    to_stage: str | None = None,
    notes: str | None = None,
) -> None:
    entry = PipelineActionLog(
        id=str(uuid4()),
        workspace_id=workspace_id,
        action=action,
        from_stage=from_stage,
        to_stage=to_stage,
        notes=notes,
        created_at=_now_iso(),
    )
    db.add(entry)
    db.commit()
    # caller is responsible for db.commit()

# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # redirect to the workspaces list
    return RedirectResponse(url="/workspaces")

@app.get("/workspaces", response_class=HTMLResponse)
async def list_workspaces(request: Request, db: Session = Depends(get_db)):
    workspaces = (
        db.query(Workspace)
        .order_by(Workspace.created_at.desc())
        .all()
    )

    return templates.TemplateResponse(
        "workspaces.html",
        {
            "request": request,
            "workspaces": workspaces,
            "workspace": None,           # no center panel yet
            "pipeline_state": None,
            "pipeline_actions": [],
            "documents": [],
            "selected_workspace_id": None,
        },
    )

@app.get("/workspaces/new", response_class=HTMLResponse)
async def new_workspace_form(request: Request):
    """
    Returns just the 'new workspace' form.
    When called via HTMX, this is injected into the page.
    """
    return templates.TemplateResponse(
        "new_workspace_form.html",
        {
            "request": request,
        },
    )


@app.post("/workspaces", response_class=HTMLResponse)
async def create_workspace(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    """
    Creates a new workspace in the database.

    If called via HTMX, we return a single <tr> row so HTMX can
    append it to the table without reloading the page.
    """
    now = _now_iso()
    workspace = Workspace(
        id=str(uuid4()),
        name=name,
        description=description,
        status="active",
        created_at=now,
        updated_at=now,
    )
    log_pipeline_action(
        db,
        workspace_id=workspace.id,
        action="workspace_created",
        notes=f"Workspace '{workspace.name}' created.",
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)

 # Create initial pipeline state for this workspace
    pipeline_state = PipelineState(
        id=str(uuid4()),
        workspace_id=workspace.id,
        stage="not_started",
        approved=False,
        created_at=now,
        updated_at=now,
    )
    db.add(pipeline_state)
    db.commit()

    log_pipeline_action(
        db,
        workspace_id=workspace.id,
        action="approve_epic",
        from_stage="epic_approval",
        to_stage="architecture_start",
        notes="User approved the epic",
    )

    is_htmx = request.headers.get("HX-Request") == "true"

    if is_htmx:
        # Return just the table row snippet
        return templates.TemplateResponse(
            "workspace_row.html",
            {
                "request": request,
                "workspace": workspace,
            },
        )
    else:
        # Normal browser POST → redirect to list
        return RedirectResponse(url="/workspaces", status_code=303)
    
@app.get("/workspaces/{workspace_id}", response_class=HTMLResponse)
async def view_workspace(
    workspace_id: str,
    request: Request,
    db: Session = Depends(get_db),
    hx_request: str | None = Header(default=None, alias="HX-Request"),
):
    workspace = (
        db.query(Workspace)
        .filter(Workspace.id == workspace_id)
        .first()
    )

    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # TODO: wire these to real tables when ready
    pipeline_state = None
    pipeline_actions = []
    documents = []
    pipeline_logs = []

    if hx_request == "true":
        # HTMX: only return the center+right panels
        return templates.TemplateResponse(
            "workspace_main.html",
            {
                "request": request,
                "workspace": workspace,
                "pipeline_state": pipeline_state,
                "pipeline_actions": pipeline_actions,
                "documents": documents,
                "pipeline_logs": pipeline_logs,
            },
        )
    else:
        # Direct browser navigation: render full page with sidebar + main
        workspaces = (
            db.query(Workspace)
            .order_by(Workspace.created_at.desc())
            .all()
        )

        return templates.TemplateResponse(
            "workspaces.html",
            {
                "request": request,
                "workspaces": workspaces,
                "workspace": workspace,
                "pipeline_state": pipeline_state,
                "pipeline_actions": pipeline_actions,
                "documents": documents,
                "pipeline_logs": pipeline_logs,
            },
        )

@app.delete("/workspaces/{workspace_id}")
async def delete_workspace(
    workspace_id: str,
    db: Session = Depends(get_db),
):
    workspace = (
        db.query(Workspace)
        .filter(Workspace.id == workspace_id)
        .first()
    )

    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # If you have these models, clean up related data too:
    # db.query(PipelineState).filter_by(workspace_id=workspace_id).delete()
    # db.query(PipelineActionLog).filter_by(workspace_id=workspace_id).delete()
    # db.query(CanonicalDocument).filter_by(workspace_id=workspace_id).delete()

    db.delete(workspace)
    db.commit()

    # HTMX: 204 with no content, and hx-target/hx-swap will handle removal
    return Response(status_code=200)

@app.post("/workspaces/{workspace_id}/start-pm-flow")
async def start_pm_flow(
    workspace_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    now = _now_iso()

    pipeline_state = (
        db.query(PipelineState)
        .filter(PipelineState.workspace_id == workspace_id)
        .first()
    )

    if pipeline_state is None:
        # First-time start: not_started -> pm_questions
        sm = PipelineStateMachine("not_started")
        sm.transition("pm_questions")

        pipeline_state = PipelineState(
            id=str(uuid4()),
            workspace_id=workspace_id,
            stage=sm.stage.value,
            approved=0,
            context=None,
            created_at=now,
            updated_at=now,
        )
        db.add(pipeline_state)

        # Log the action
        log_pipeline_action(
            db,
            workspace_id=workspace.id,
            action="pm_flow_started",
            from_stage=pipeline_state.stage if pipeline_state else None,
            to_stage="pm_questions",
            notes="PM flow initiated."
        )

    else:
        # Subsequent calls: enforce legal transition via state machine
        sm = PipelineStateMachine(pipeline_state.stage)
        from_stage = pipeline_state.stage

        try:
            sm.transition("pm_questions")
        except InvalidPipelineTransition as e:
            raise HTTPException(status_code=400, detail=str(e))

        pipeline_state.stage = sm.stage.value
        pipeline_state.updated_at = now

        log_pipeline_action(
            db,
            workspace_id=workspace_id,
            action="start_pm_flow",
            from_stage=from_stage,
            to_stage=sm.stage.value,
            notes="PM flow re-start requested",
        )

    db.commit()

    return RedirectResponse(
        url=f"/workspaces/{workspace_id}",
        status_code=303,
    )

