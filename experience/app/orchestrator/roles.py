from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
import json

# This file should live at: experience/app/orchestrator/roles.py
# Repo structure assumed:
#   experience/
#     app/
#       orchestrator/
#         roles.py   <-- this file
#     workbench/
#       shared/
#         *.md
#       roles/
#         <role>/
#           bootstrap.md
#           instructions.md
#           schemas.json (optional)

# This file should live at: <repo_root>/experience/app/orchestrator/roles.py

HERE = Path(__file__).resolve()
# repo_root: .../workbench
#   roles.py: .../workbench/experience/app/orchestrator/roles.py
#   parents[0] = .../experience/app
#   parents[1] = .../experience
#   parents[2] = .../workbench  <-- repo root
REPO_ROOT = HERE.parents[4]
# We expect role instructions under <repo_root>/workbench/
WORKBENCH_DIR = REPO_ROOT / "workbench"
ROLES_DIR = WORKBENCH_DIR / "roles"
SHARED_DIR = WORKBENCH_DIR / "shared"

CANONICAL_DOC_PATHS = {
    "canonical_backlog": SHARED_DIR / "canonical_backlog.json",
    "canonical_architecture": SHARED_DIR / "canonical_architecture.json",
    "canonical_epic": SHARED_DIR / "canonical_epic.json",
}
@dataclass
class RoleConfig:
    """
    In-memory representation of a Workforce role's configuration.
    """
    name: str                           # e.g. "pm", "developer"
    bootstrap: str                      # contents of bootstrap.md
    instructions: str                   # contents of instructions.md
    schemas: Optional[Dict[str, Any]]   # parsed schemas.json, if present
    shared_docs: Dict[str, str]         # all shared/*.md, keyed by stem (e.g. "domain_overview")
    canonical_docs: Dict[str, str] = None   # <--- NEW

def load_shared_docs() -> Dict[str, str]:
    """
    Load all markdown files in workbench/shared into a dict:
      { "domain_overview": "...", "glossary": "...", ... }
    """
    docs: Dict[str, str] = {}

    if not SHARED_DIR.exists():
        # It's valid to run tests before the workbench/ tree exists.
        return docs

    for path in SHARED_DIR.glob("*.md"):
        try:
            docs[path.stem] = path.read_text(encoding="utf-8")
        except OSError:
            # Fail soft; individual missing/unreadable shared docs shouldn't crash the orchestrator
            continue

    return docs

def load_canonical_docs() -> Dict[str, str]:
    """
    Load canonical JSON docs (backlog, architecture, epic model) and
    return them as pretty-printed JSON strings.
    """
    docs: Dict[str, str] = {}

    for key, path in CANONICAL_DOC_PATHS.items():
        if not path.exists():
            continue
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
            docs[key] = json.dumps(obj, indent=2)
        except json.JSONDecodeError:
            # If it's not valid JSON for some reason, just pass through raw text
            docs[key] = raw

    return docs


def load_role_config(role_name: str, shared_docs: Dict[str, str]) -> RoleConfig:
    """
    Load a single role's configuration from workbench/roles/<role_name>/.
    Requires bootstrap.md and instructions.md. schemas.json is optional.
    """
    role_dir = ROLES_DIR / role_name

    if not role_dir.exists():
        raise FileNotFoundError(f"Role directory not found: {role_dir}")

    bootstrap_path = role_dir / "bootstrap.md"
    instructions_path = role_dir / "instructions.md"
    schemas_path = role_dir / "schemas.json"

    if not bootstrap_path.exists():
        raise FileNotFoundError(f"Missing bootstrap.md for role '{role_name}' in {role_dir}")
    if not instructions_path.exists():
        raise FileNotFoundError(f"Missing instructions.md for role '{role_name}' in {role_dir}")

    bootstrap = bootstrap_path.read_text(encoding="utf-8")
    instructions = instructions_path.read_text(encoding="utf-8")

    schemas: Optional[Dict[str, Any]] = None
    if schemas_path.exists():
        raw = schemas_path.read_text(encoding="utf-8")
        # Empty or whitespace-only schemas.json is treated as "no schemas"
        if raw.strip():
            schemas = json.loads(raw)

    return RoleConfig(
        name=role_name,
        bootstrap=bootstrap,
        instructions=instructions,
        schemas=schemas,
        shared_docs=shared_docs,
    )


def build_role_registry() -> Dict[str, RoleConfig]:
    """
    Discover all roles under workbench/roles and build a registry:
      { "pm": RoleConfig(...), "developer": RoleConfig(...), ... }
    """
    shared_docs = load_shared_docs()
    canonical_docs = load_canonical_docs()
    registry: Dict[str, RoleConfig] = {}

    if not ROLES_DIR.exists():
        # If roles/ doesn't exist yet, return an empty registry.
        return registry

    for role_dir in ROLES_DIR.iterdir():
        if not role_dir.is_dir():
            continue
        role_name = role_dir.name  # e.g. "pm", "developer", "developer_mentor"
        try:
            cfg = load_role_config(role_name, shared_docs)
            registry[role_name] = load_role_config(role_name, shared_docs)
        except FileNotFoundError:
            # Skip incomplete role definitions rather than crashing everything.
            continue

        # Attach canonical docs
        cfg.canonical_docs = canonical_docs
        registry[role_name] = cfg

    return registry


def get_role_config(
    role_name: str,
    registry: Optional[Dict[str, RoleConfig]] = None,
) -> RoleConfig:
    """
    Convenience accessor. If no registry is provided, build one on demand.
    """
    if registry is None:
        registry = build_role_registry()

    try:
        return registry[role_name]
    except KeyError as exc:
        raise KeyError(f"Role '{role_name}' not found in role registry") from exc


def build_role_prompt(
    role_name: str,
    ticket_context: Optional[str] = None,
    registry: Optional[Dict[str, RoleConfig]] = None,
) -> str:
    """
    Assemble a full system prompt for a given role, including:
      - bootstrap
      - shared domain docs
      - role-specific instructions
      - optional ticket-specific context

    `ticket_context` is free-form text you (Tom/orchestrator) can pass in,
    e.g. the AUTH-101 ticket summary, current UX snippet, etc.
    """
    config = get_role_config(role_name, registry)

    domain_overview = config.shared_docs.get("domain_overview", "")
    glossary = config.shared_docs.get("glossary", "")
    style_guide = config.shared_docs.get("style_guide", "")
    architecture_overview = config.shared_docs.get("architecture_overview", "")
    backlog_overview = config.shared_docs.get("backlog_overview", "")
    canonical_backlog = config.canonical_docs.get("canonical_backlog", "")
    canonical_architecture = config.canonical_docs.get("canonical_architecture", "")
    canonical_epic = config.canonical_docs.get("canonical_epic", "")
    # Schemas are represented as JSON; we inline them pretty-printed if present.
    schemas_block = ""
    if config.schemas:
        # This is intended for LLM consumption, so human-readable formatting helps.
        pretty = json.dumps(config.schemas, indent=2)
        schemas_block = f"\n\n### Schemas\n\n```json\n{pretty}\n```"

    ticket_block = ""
    if ticket_context:
        ticket_block = f"\n\n### Ticket Context\n\n{ticket_context.strip()}"

    prompt = f"""
You are the **{role_name}** in the Workbench Workforce.

{config.bootstrap.strip()}

# Shared Domain Overview

{domain_overview.strip()}

# Glossary

{glossary.strip()}

# Style Guide

{style_guide.strip()}

# Canonical Backlog (JSON)

https://raw.githubusercontent.com/tommoseley/Workbench-AI/refs/heads/main/docs/Workbench%20AI%20-%20Canonical%20Backlog.json

# Canonical Architecture (JSON)

https://raw.githubusercontent.com/tommoseley/Workbench-AI/refs/heads/main/shared/canonical_architecture.json

# Canonical Epic (JSON)

https://raw.githubusercontent.com/tommoseley/Workbench-AI/refs/heads/main/shared/canonical_epic.json

# Architecture Overview

{architecture_overview.strip()}

# Backlog Overview

{backlog_overview.strip()}

# Role Instructions

{config.instructions.strip()}
{schemas_block}
{ticket_block}
""".strip()

    return prompt
