"""
Workspace scaffolders: create/delete operations for config artifacts.

Functions for scaffolding new orchestration workflows, document types,
DCW workflows, role prompts, templates, and standalone schemas.
Extracted from workspace_service.py.
"""

import json
import re
import shutil
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

from app.api.services.release_manager import (
    update_active_releases_for_doc_type,
    update_active_releases_for_role,
    update_active_releases_for_schema,
    update_active_releases_for_template,
    update_active_releases_for_workflow,
)


class ScaffoldError(Exception):
    """Error during scaffold operations."""
    pass


class ScaffoldNotFoundError(ScaffoldError):
    """Artifact not found for scaffold operation."""
    pass


def _validate_snake_case_id(value: str, label: str) -> None:
    """Validate that value matches snake_case pattern."""
    if not re.match(r'^[a-z][a-z0-9_]*$', value):
        raise ScaffoldError(
            f"Invalid {label}: '{value}'. "
            f"Must match pattern: ^[a-z][a-z0-9_]*$"
        )


def _auto_display_name(snake_id: str) -> str:
    """Convert snake_case ID to Title Case display name."""
    return snake_id.replace('_', ' ').title()


# =========================================================================
# Orchestration Workflow
# =========================================================================

def create_orchestration_workflow(
    config_path: Path,
    workflow_id: str,
    name: Optional[str] = None,
    version: str = "1.0.0",
    pow_class: str = "template",
    derived_from: Optional[Dict[str, str]] = None,
    source_version: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> str:
    """
    Create a new orchestration workflow definition.

    Creates the directory structure, skeleton definition.json,
    and updates active_releases.json.

    Args:
        config_path: Path to combine-config directory
        workflow_id: Workflow ID (snake_case)
        name: Display name (auto-generated from workflow_id if None)
        version: Initial version
        pow_class: Classification (reference, template, instance)
        derived_from: Source workflow reference {workflow_id, version}
        source_version: Version of source at fork time
        tags: Free-form classification tags

    Returns:
        Artifact ID for the new workflow
    """
    _validate_snake_case_id(workflow_id, "workflow_id")

    # Check if workflow already exists
    workflow_dir = config_path / "workflows" / workflow_id
    if workflow_dir.exists():
        raise ScaffoldError(f"Workflow already exists: {workflow_id}")

    # Auto-generate display name
    if not name:
        name = _auto_display_name(workflow_id)

    # Create directory structure and definition.json
    release_dir = workflow_dir / "releases" / version
    release_dir.mkdir(parents=True, exist_ok=True)

    skeleton = {
        "schema_version": "workflow.v2",
        "workflow_id": workflow_id,
        "revision": f"wfrev_{date.today().isoformat().replace('-', '_')}_a",
        "effective_date": date.today().isoformat(),
        "name": name,
        "description": "",
        "pow_class": pow_class,
        "derived_from": derived_from,
        "source_version": source_version,
        "tags": tags or [],
        "scopes": {
            "project": {"parent": None}
        },
        "document_types": {},
        "entity_types": {},
        "steps": []
    }

    definition_path = release_dir / "definition.json"
    definition_path.write_text(
        json.dumps(skeleton, indent=2),
        encoding="utf-8",
    )

    # Update active_releases.json
    update_active_releases_for_workflow(config_path, workflow_id, version)

    return f"workflow:{workflow_id}:{version}:definition"


def delete_orchestration_workflow(
    config_path: Path,
    workflow_id: str,
) -> None:
    """
    Delete an orchestration workflow.

    Removes the workflow directory and updates active_releases.json.

    Args:
        config_path: Path to combine-config directory
        workflow_id: Workflow ID to delete
    """
    # Verify workflow exists
    workflow_dir = config_path / "workflows" / workflow_id
    if not workflow_dir.exists():
        raise ScaffoldNotFoundError(f"Workflow not found: {workflow_id}")

    # Verify it's step-based (not graph-based)
    for def_file in workflow_dir.rglob("definition.json"):
        try:
            with open(def_file, "r", encoding="utf-8-sig") as f:
                raw = json.load(f)
            if "nodes" in raw and "edges" in raw:
                raise ScaffoldError(
                    f"Cannot delete graph-based workflow '{workflow_id}' "
                    f"via this endpoint. Use the document type workflow editor."
                )
        except json.JSONDecodeError:
            pass
        break

    # Remove directory tree
    shutil.rmtree(workflow_dir)

    # Update active_releases.json
    update_active_releases_for_workflow(config_path, workflow_id, None)


# =========================================================================
# Document Type
# =========================================================================

def create_document_type(
    config_path: Path,
    doc_type_id: str,
    display_name: Optional[str] = None,
    version: str = "1.0.0",
    scope: str = "project",
    role_ref: str = "prompt:role:technical_architect:1.0.0",
) -> str:
    """
    Create a new document type definition (DCW).

    Creates the directory structure, skeleton package.yaml,
    empty prompt files, and updates active_releases.json.

    Args:
        config_path: Path to combine-config directory
        doc_type_id: Document type ID (snake_case)
        display_name: Display name (auto-generated from doc_type_id if None)
        version: Initial version
        scope: Scope level (project, epic, etc.)
        role_ref: Reference to role prompt

    Returns:
        Artifact ID for the new document type
    """
    _validate_snake_case_id(doc_type_id, "doc_type_id")

    # Check if document type already exists
    doc_type_dir = config_path / "document_types" / doc_type_id
    if doc_type_dir.exists():
        raise ScaffoldError(f"Document type already exists: {doc_type_id}")

    # Auto-generate display name
    if not display_name:
        display_name = _auto_display_name(doc_type_id)

    # Create directory structure
    release_dir = doc_type_dir / "releases" / version
    prompts_dir = release_dir / "prompts"
    schemas_dir = release_dir / "schemas"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    schemas_dir.mkdir(parents=True, exist_ok=True)

    # Create package.yaml skeleton
    package_yaml = f"""# Document Type Package Manifest
# Schema: ../../../schemas/registry/package.schema.json

doc_type_id: {doc_type_id}
display_name: {display_name}
version: {version}

description: >
  TODO: Add description for this document type.

# Classification (per ADR-044)
authority_level: descriptive
creation_mode: llm_generated
production_mode: generate
scope: {scope}

# Dependencies
required_inputs: []
optional_inputs: []

# Shared artifact references
role_prompt_ref: "{role_ref}"
template_ref: "prompt:template:document_generator:1.0.0"
qa_template_ref: "prompt:template:qa_evaluator:1.0.0"
pgc_template_ref: "prompt:template:pgc_clarifier:1.0.0"
schema_ref: "schema:{doc_type_id}:{version}"

# Packaged artifacts (relative paths)
artifacts:
  task_prompt: prompts/task.prompt.txt
  qa_prompt: prompts/qa.prompt.txt
  pgc_context: prompts/pgc_context.prompt.txt
  schema: schemas/output.schema.json

# Test artifacts
tests:
  fixtures: []
  golden_traces: []

# UI configuration
ui:
  icon: document
  category: general
  display_order: 100
"""
    (release_dir / "package.yaml").write_text(package_yaml, encoding="utf-8")

    # Create skeleton prompt files
    task_prompt = f"""# Task Prompt for {display_name}

You are producing a {display_name} document.

## Instructions

TODO: Add task instructions here.

## Output Requirements

Produce a structured JSON document following the output schema.
"""
    (prompts_dir / "task.prompt.txt").write_text(task_prompt, encoding="utf-8")

    qa_prompt = f"""# QA Prompt for {display_name}

Evaluate the {display_name} document for quality and completeness.

## Evaluation Criteria

TODO: Add evaluation criteria here.
"""
    (prompts_dir / "qa.prompt.txt").write_text(qa_prompt, encoding="utf-8")

    pgc_prompt = f"""# PGC Context for {display_name}

Context for pre-generation clarification.

## Areas to Clarify

TODO: Add clarification areas here.
"""
    (prompts_dir / "pgc_context.prompt.txt").write_text(pgc_prompt, encoding="utf-8")

    # Create skeleton schema
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"schema:{doc_type_id}:{version}",
        "title": display_name,
        "description": f"Output schema for {display_name}",
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Document title"
            },
            "content": {
                "type": "string",
                "description": "Main content"
            }
        },
        "required": ["title", "content"]
    }
    (schemas_dir / "output.schema.json").write_text(
        json.dumps(schema, indent=2),
        encoding="utf-8",
    )

    # Update active_releases.json
    update_active_releases_for_doc_type(config_path, doc_type_id, version)

    return f"doctype:{doc_type_id}:{version}:package"


def delete_document_type(
    config_path: Path,
    doc_type_id: str,
) -> None:
    """
    Delete a document type definition.

    Removes the document type directory and updates active_releases.json.

    Args:
        config_path: Path to combine-config directory
        doc_type_id: Document type ID to delete
    """
    # Verify document type exists
    doc_type_dir = config_path / "document_types" / doc_type_id
    if not doc_type_dir.exists():
        raise ScaffoldNotFoundError(f"Document type not found: {doc_type_id}")

    # Remove directory tree
    shutil.rmtree(doc_type_dir)

    # Update active_releases.json
    update_active_releases_for_doc_type(config_path, doc_type_id, None)


# =========================================================================
# DCW Workflow (Graph-based workflows for document types)
# =========================================================================

def create_dcw_workflow(
    config_path: Path,
    doc_type_id: str,
    version: str = "1.0.0",
) -> str:
    """
    Create a graph-based workflow definition for a document type.

    Creates the workflow directory structure with a skeleton definition.json
    containing PGC, generation, QA, remediation nodes and standard edges.

    Args:
        config_path: Path to combine-config directory
        doc_type_id: Document type ID (must exist)
        version: Initial version

    Returns:
        Artifact ID for the new workflow
    """
    _validate_snake_case_id(doc_type_id, "doc_type_id")

    # Verify document type exists
    doc_type_dir = config_path / "document_types" / doc_type_id
    if not doc_type_dir.exists():
        raise ScaffoldError(f"Document type not found: {doc_type_id}")

    # Check if workflow already exists
    workflow_dir = config_path / "workflows" / doc_type_id
    if workflow_dir.exists():
        raise ScaffoldError(f"Workflow already exists: {doc_type_id}")

    # Create display name
    display_name = _auto_display_name(doc_type_id)

    # Create directory structure and definition.json
    release_dir = workflow_dir / "releases" / version
    release_dir.mkdir(parents=True, exist_ok=True)

    skeleton = {
        "$schema": "https://thecombine.ai/schemas/workflow-plan.v1.json",
        "workflow_id": doc_type_id,
        "version": version,
        "name": f"{display_name} Workflow",
        "description": f"Document creation workflow for {display_name}",
        "scope_type": "document",
        "document_type": doc_type_id,
        "thread_ownership": {
            "owns_thread": False,
            "thread_purpose": None
        },
        "entry_node_ids": ["pgc"],
        "nodes": [
            {
                "node_id": "pgc",
                "type": "pgc",
                "description": f"Pre-generation clarification for {display_name}",
                "task_ref": "clarification_questions_generator",
                "includes": {},
                "_position": {"x": 50, "y": 40}
            },
            {
                "node_id": "generation",
                "type": "task",
                "description": f"Generate {display_name} document",
                "task_ref": "document_generator",
                "includes": {},
                "produces": doc_type_id,
                "_position": {"x": -220, "y": 235}
            },
            {
                "node_id": "qa",
                "type": "qa",
                "description": f"QA evaluation for {display_name}",
                "task_ref": f"tasks/{display_name} QA v1.0",
                "requires_qa": True,
                "qa_mode": "semantic",
                "_position": {"x": 65, "y": 390}
            },
            {
                "node_id": "remediation",
                "type": "task",
                "description": f"Rework {display_name} based on QA feedback",
                "task_ref": "document_generator",
                "includes": {},
                "produces": doc_type_id,
                "_position": {"x": 50, "y": 200}
            },
            {
                "node_id": "end_complete",
                "type": "end",
                "description": f"{display_name} document ready",
                "terminal_outcome": "stabilized",
                "gate_outcome": "complete",
                "_position": {"x": -160, "y": 800}
            },
            {
                "node_id": "end_failed",
                "type": "end",
                "description": "Generation failed",
                "terminal_outcome": "blocked",
                "gate_outcome": "failed",
                "_position": {"x": 190, "y": 800}
            }
        ],
        "edges": [
            {
                "edge_id": "pgc_to_generation",
                "from_node_id": "pgc",
                "to_node_id": "generation",
                "outcome": "success",
                "label": "Clarification complete, proceed to generation",
                "kind": "auto"
            },
            {
                "edge_id": "pgc_needs_answers",
                "from_node_id": "pgc",
                "to_node_id": None,
                "outcome": "needs_user_input",
                "label": "User must answer clarification questions",
                "kind": "auto",
                "non_advancing": True
            },
            {
                "edge_id": "generation_to_qa",
                "from_node_id": "generation",
                "to_node_id": "qa",
                "outcome": "success",
                "label": "Document generated, run QA",
                "kind": "auto"
            },
            {
                "edge_id": "generation_failed",
                "from_node_id": "generation",
                "to_node_id": "end_failed",
                "outcome": "failed",
                "label": "Document generation failed",
                "kind": "auto"
            },
            {
                "edge_id": "qa_pass",
                "from_node_id": "qa",
                "to_node_id": "end_complete",
                "outcome": "success",
                "label": "QA passed - document complete",
                "kind": "auto"
            },
            {
                "edge_id": "qa_fail_remediate",
                "from_node_id": "qa",
                "to_node_id": "remediation",
                "outcome": "failed",
                "label": "QA failed, remediate",
                "kind": "auto",
                "conditions": [{"type": "retry_count", "operator": "lt", "value": 2}]
            },
            {
                "edge_id": "qa_fail_circuit_breaker",
                "from_node_id": "qa",
                "to_node_id": "end_failed",
                "outcome": "failed",
                "label": "QA failed, circuit breaker",
                "kind": "auto",
                "conditions": [{"type": "retry_count", "operator": "gte", "value": 2}]
            },
            {
                "edge_id": "remediation_to_qa",
                "from_node_id": "remediation",
                "to_node_id": "qa",
                "outcome": "success",
                "label": "Remediation complete, re-run QA",
                "kind": "auto"
            },
            {
                "edge_id": "remediation_failed",
                "from_node_id": "remediation",
                "to_node_id": "end_failed",
                "outcome": "failed",
                "label": "Remediation failed",
                "kind": "auto"
            }
        ],
        "governance": {
            "adr_references": [],
            "design_principles": [
                "Auto-complete on QA pass",
                "PGC clarification before generation"
            ],
            "circuit_breaker": {
                "max_retries": 2,
                "applies_to": ["qa", "remediation"],
                "on_trip": "end_failed with internal error flag"
            }
        },
        "metadata": {
            "created_date": date.today().isoformat(),
            "updated_date": date.today().isoformat(),
            "changelog": [f"v{version}: Initial workflow created"]
        },
        "requires_inputs": []
    }

    definition_path = release_dir / "definition.json"
    definition_path.write_text(
        json.dumps(skeleton, indent=2),
        encoding="utf-8",
    )

    # Update active_releases.json
    update_active_releases_for_workflow(config_path, doc_type_id, version)

    return f"workflow:{doc_type_id}:{version}:definition"


# =========================================================================
# Role Prompt
# =========================================================================

def create_role_prompt(
    config_path: Path,
    role_id: str,
    name: Optional[str] = None,
    version: str = "1.0.0",
) -> str:
    """
    Create a new role prompt.

    Creates the directory structure, skeleton role.prompt.txt,
    meta.yaml, and updates active_releases.json.

    Args:
        config_path: Path to combine-config directory
        role_id: Role ID (snake_case)
        name: Display name (auto-generated if None)
        version: Initial version

    Returns:
        Artifact ID for the new role
    """
    import yaml as _yaml

    _validate_snake_case_id(role_id, "role_id")

    # Check if role already exists
    role_dir = config_path / "prompts" / "roles" / role_id
    if role_dir.exists():
        raise ScaffoldError(f"Role already exists: {role_id}")

    # Auto-generate display name
    if not name:
        name = _auto_display_name(role_id)

    # Create directory structure
    release_dir = role_dir / "releases" / version
    release_dir.mkdir(parents=True, exist_ok=True)

    # Create skeleton role prompt
    role_prompt = f"""# {name} Role Prompt

You are a {name.lower()}.

## Responsibilities

TODO: Define the role's responsibilities.

## Constraints

TODO: Define any constraints or guidelines.

## Output Style

TODO: Define the expected output style.
"""
    (release_dir / "role.prompt.txt").write_text(role_prompt, encoding="utf-8")

    # Create meta.yaml
    meta_content = _yaml.dump({
        "name": name,
        "intent": None,
        "tags": [],
    }, default_flow_style=False)
    (release_dir / "meta.yaml").write_text(meta_content, encoding="utf-8")

    # Update active_releases.json
    update_active_releases_for_role(config_path, role_id, version)

    return f"role:{role_id}:{version}:role_prompt"


# =========================================================================
# Template
# =========================================================================

def create_template(
    config_path: Path,
    template_id: str,
    name: Optional[str] = None,
    purpose: str = "general",
    version: str = "1.0.0",
) -> str:
    """
    Create a new template.

    Creates the directory structure, skeleton template.txt,
    meta.yaml, and updates active_releases.json.

    Args:
        config_path: Path to combine-config directory
        template_id: Template ID (snake_case)
        name: Display name (auto-generated if None)
        purpose: Template purpose (document, qa, pgc, general)
        version: Initial version

    Returns:
        Artifact ID for the new template
    """
    import yaml as _yaml

    _validate_snake_case_id(template_id, "template_id")

    # Check if template already exists
    template_dir = config_path / "prompts" / "templates" / template_id
    if template_dir.exists():
        raise ScaffoldError(f"Template already exists: {template_id}")

    # Auto-generate display name
    if not name:
        name = _auto_display_name(template_id)

    # Create directory structure
    release_dir = template_dir / "releases" / version
    release_dir.mkdir(parents=True, exist_ok=True)

    # Create skeleton template
    template_content = f"""# {name} Template

$$ROLE_PROMPT

---

$$TASK_PROMPT

---

## Output Schema

$$OUTPUT_SCHEMA

---

Please produce a response conforming to the output schema.
"""
    (release_dir / "template.txt").write_text(template_content, encoding="utf-8")

    # Create meta.yaml
    meta_content = _yaml.dump({
        "name": name,
        "purpose": purpose,
        "use_case": None,
    }, default_flow_style=False)
    (release_dir / "meta.yaml").write_text(meta_content, encoding="utf-8")

    # Update active_releases.json
    update_active_releases_for_template(config_path, template_id, version)

    return f"template:{template_id}:{version}:template"


# =========================================================================
# Standalone Schema
# =========================================================================

def create_standalone_schema(
    config_path: Path,
    schema_id: str,
    title: Optional[str] = None,
    version: str = "1.0.0",
) -> str:
    """
    Create a new standalone schema.

    Creates the directory structure, skeleton schema.json,
    and updates active_releases.json.

    Args:
        config_path: Path to combine-config directory
        schema_id: Schema ID (snake_case)
        title: Schema title (auto-generated if None)
        version: Initial version

    Returns:
        Artifact ID for the new schema
    """
    _validate_snake_case_id(schema_id, "schema_id")

    # Check if schema already exists
    schema_dir = config_path / "schemas" / schema_id
    if schema_dir.exists():
        raise ScaffoldError(f"Schema already exists: {schema_id}")

    # Auto-generate title
    if not title:
        title = _auto_display_name(schema_id)

    # Create directory structure
    release_dir = schema_dir / "releases" / version
    release_dir.mkdir(parents=True, exist_ok=True)

    # Create skeleton schema
    schema_content = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"schema:{schema_id}:{version}",
        "title": title,
        "description": f"Schema for {title}",
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "Main content"
            }
        },
        "required": ["content"]
    }
    (release_dir / "schema.json").write_text(
        json.dumps(schema_content, indent=2),
        encoding="utf-8",
    )

    # Update active_releases.json
    update_active_releases_for_schema(config_path, schema_id, version)

    return f"schema:{schema_id}:{version}:schema"
