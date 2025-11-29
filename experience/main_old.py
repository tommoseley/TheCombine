from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from uuid import uuid4
from datetime import datetime

app = FastAPI()

templates = Jinja2Templates(directory="templates")

# --- In-memory store for now (we'll swap this for SQLite/SQLAlchemy later) ---
WORKSPACES: list[dict] = []


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


# Seed with a couple of fake rows so the table isn't empty
if not WORKSPACES:
    WORKSPACES.append({
        "id": str(uuid4()),
        "name": "Sample Workspace A",
        "description": "First example workspace",
        "status": "active",
        "created_at": _now_iso(),
    })
    WORKSPACES.append({
        "id": str(uuid4()),
        "name": "Sample Workspace B",
        "description": "Second example workspace",
        "status": "active",
        "created_at": _now_iso(),
    })


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # redirect to the workspaces list
    return RedirectResponse(url="/workspaces")


@app.get("/workspaces", response_class=HTMLResponse)
async def list_workspaces(request: Request):
    """
    Full page: list of workspaces.
    """
    return templates.TemplateResponse(
        "workspaces.html",
        {
            "request": request,
            "workspaces": WORKSPACES,
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
):
    """
    Creates a new workspace.

    If called via HTMX, we return a single <tr> row so HTMX can
    append it to the table without reloading the page.
    """
    workspace = {
        "id": str(uuid4()),
        "name": name,
        "description": description,
        "status": "active",
        "created_at": _now_iso(),
    }
    WORKSPACES.append(workspace)

    # HTMX sends HX-Request: true header
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
