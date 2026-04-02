"""
Artifact ID resolution: parsing and path mapping.

Pure functions for converting between artifact IDs and file paths
within combine-config. Extracted from workspace_service.py.
"""

import re
from typing import Dict, Optional


class ArtifactIdError(Exception):
    """Invalid artifact ID format."""
    pass


# =========================================================================
# Dispatch tables (module-level constants)
# =========================================================================

# Outer key = scope, inner key = kind, value = path template.
# Templates use {name} and {version} placeholders.
SCOPE_KIND_PATHS = {
    "doctype": {
        "task_prompt": "document_types/{name}/releases/{version}/prompts/task.prompt.txt",
        "qa_prompt": "document_types/{name}/releases/{version}/prompts/qa.prompt.txt",
        "reflection_prompt": "document_types/{name}/releases/{version}/prompts/reflection.prompt.txt",
        "pgc_context": "document_types/{name}/releases/{version}/prompts/pgc_context.prompt.txt",
        "questions_prompt": "document_types/{name}/releases/{version}/prompts/questions.prompt.txt",
        "schema": "document_types/{name}/releases/{version}/schemas/output.schema.json",
        "manifest": "document_types/{name}/releases/{version}/package.yaml",
        "package": "document_types/{name}/releases/{version}/package.yaml",  # alias for manifest
    },
    "role": {
        "role_prompt": "prompts/roles/{name}/releases/{version}/role.prompt.txt",
    },
    "template": {
        "template": "prompts/templates/{name}/releases/{version}/template.txt",
        "meta": "prompts/templates/{name}/releases/{version}/meta.yaml",
    },
    "workflow": {
        "definition": "workflows/{name}/releases/{version}/definition.json",
    },
    "schema": {
        "schema": "schemas/{name}/releases/{version}/schema.json",
    },
}

# Fragment dispatch: keyed by (frag_kind, artifact_kind).
# Templates use {frag_id} and {version} placeholders.
FRAGMENT_PATHS = {
    ("role", "content"): "prompts/roles/{frag_id}/releases/{version}/role.prompt.txt",
    ("role", "meta"): "prompts/roles/{frag_id}/releases/{version}/meta.yaml",
    ("task", "content"): "prompts/tasks/{frag_id}/releases/{version}/task.prompt.txt",
    ("task", "meta"): "prompts/tasks/{frag_id}/releases/{version}/meta.yaml",
    ("pgc", "content"): "prompts/pgc/{frag_id}/releases/{version}/pgc_context.prompt.txt",
    ("pgc", "meta"): "prompts/pgc/{frag_id}/releases/{version}/meta.yaml",
}

# Doctype-prompt fragment kinds that share the same path pattern.
DOCTYPE_PROMPT_FRAG_KINDS = frozenset({"task", "qa", "pgc", "questions", "reflection"})

# Maps doctype-prompt frag_kind to its prompt file subpath.
FRAG_KIND_TO_PROMPT_FILE = {
    "task": "prompts/task.prompt.txt",
    "qa": "prompts/qa.prompt.txt",
    "pgc": "prompts/pgc_context.prompt.txt",
    "questions": "prompts/questions.prompt.txt",
    "reflection": "prompts/reflection.prompt.txt",
}


# =========================================================================
# Pure functions
# =========================================================================

def parse_artifact_id(artifact_id: str) -> Dict[str, str]:
    """
    Parse artifact ID into components.

    Format: {scope}:{name}:{version}:{kind}

    Special case for fragments:
    Format: fragment:{frag_kind}:{frag_id}:{version}:{kind}
    Example: fragment:role:technical_architect:1.0.0:content
    The name becomes "{frag_kind}:{frag_id}" (e.g., "role:technical_architect")

    Examples:
    - doctype:project_discovery:1.4.0:task_prompt
    - role:technical_architect:1.0.0:role_prompt
    - template:document_generator:1.0.0:template
    - fragment:role:technical_architect:1.0.0:content

    Returns:
        Dict with scope, name, version, kind
    """
    parts = artifact_id.split(":")

    # Handle fragment scope specially - it has 5 parts
    # fragment:{frag_kind}:{frag_id}:{version}:{kind}
    if len(parts) == 5 and parts[0] == "fragment":
        scope = parts[0]
        name = f"{parts[1]}:{parts[2]}"  # e.g., "role:technical_architect"
        version = parts[3]
        kind = parts[4]
    elif len(parts) == 4:
        scope, name, version, kind = parts
    else:
        raise ArtifactIdError(
            f"Invalid artifact ID format: {artifact_id}. "
            f"Expected {{scope}}:{{name}}:{{version}}:{{kind}}"
        )

    if scope not in ("doctype", "role", "template", "workflow", "fragment", "schema"):
        raise ArtifactIdError(
            f"Invalid scope '{scope}' in artifact ID. "
            f"Expected: doctype, role, template, workflow, fragment, or schema"
        )

    return {
        "scope": scope,
        "name": name,
        "version": version,
        "kind": kind,
    }


def resolve_fragment_path(name: str, version: str, kind: str) -> str:
    """
    Resolve file path for a fragment artifact.

    Args:
        name: Fragment name in format "{frag_kind}:{frag_id}"
        version: Version string
        kind: Artifact kind (content, meta, etc.)

    Returns:
        File path string
    """
    frag_parts = name.split(":", 1)
    if len(frag_parts) != 2:
        raise ArtifactIdError(
            f"Invalid fragment name format: {name}. "
            f"Expected {{kind}}:{{id}} (e.g., role:technical_architect)"
        )
    frag_kind, frag_id = frag_parts

    # Check role/meta fragments first.
    role_template = FRAGMENT_PATHS.get((frag_kind, kind))
    if role_template is not None:
        return role_template.format(frag_id=frag_id, version=version)

    # Doctype-prompt fragments (task, qa, pgc, questions, reflection).
    if frag_kind in DOCTYPE_PROMPT_FRAG_KINDS:
        if kind == "content":
            prompt_file = FRAG_KIND_TO_PROMPT_FILE[frag_kind]
            return f"document_types/{frag_id}/releases/{version}/{prompt_file}"
        elif kind == "meta":
            return f"document_types/{frag_id}/releases/{version}/prompts/{frag_kind}.meta.yaml"
        else:
            raise ArtifactIdError(f"Unknown artifact kind for {frag_kind} fragment: {kind}")

    # If frag_kind is "role" but kind was not content/meta, it wasn't in FRAGMENT_PATHS.
    if frag_kind == "role":
        raise ArtifactIdError(f"Unknown artifact kind for role fragment: {kind}")

    raise ArtifactIdError(f"Unknown fragment kind: {frag_kind}")


def artifact_id_to_path(artifact_id: str) -> str:
    """
    Convert artifact ID to file path (relative to combine-config).

    Returns:
        File path string
    """
    parsed = parse_artifact_id(artifact_id)
    scope = parsed["scope"]
    name = parsed["name"]
    version = parsed["version"]
    kind = parsed["kind"]

    # Non-fragment scopes: straight dispatch table lookup.
    if scope != "fragment":
        kind_map = SCOPE_KIND_PATHS.get(scope)
        if kind_map is None:
            raise ArtifactIdError(f"Unknown scope: {scope}")
        template = kind_map.get(kind)
        if template is None:
            raise ArtifactIdError(f"Unknown artifact kind for {scope}: {kind}")
        return template.format(name=name, version=version)

    # Fragment scope: name is "{frag_kind}:{frag_id}".
    return resolve_fragment_path(name, version, kind)


def path_to_artifact_id(file_path: str) -> Optional[str]:
    """
    Convert file path to artifact ID.

    Returns:
        Artifact ID or None if not mappable
    """
    # Document type artifacts
    match = re.match(
        r"document_types/([^/]+)/releases/([^/]+)/prompts/task\.prompt\.txt$",
        file_path
    )
    if match:
        return f"doctype:{match.group(1)}:{match.group(2)}:task_prompt"

    match = re.match(
        r"document_types/([^/]+)/releases/([^/]+)/prompts/qa\.prompt\.txt$",
        file_path
    )
    if match:
        return f"doctype:{match.group(1)}:{match.group(2)}:qa_prompt"

    match = re.match(
        r"document_types/([^/]+)/releases/([^/]+)/prompts/reflection\.prompt\.txt$",
        file_path
    )
    if match:
        return f"doctype:{match.group(1)}:{match.group(2)}:reflection_prompt"

    match = re.match(
        r"document_types/([^/]+)/releases/([^/]+)/prompts/pgc_context\.prompt\.txt$",
        file_path
    )
    if match:
        return f"doctype:{match.group(1)}:{match.group(2)}:pgc_context"

    match = re.match(
        r"document_types/([^/]+)/releases/([^/]+)/schemas/output\.schema\.json$",
        file_path
    )
    if match:
        return f"doctype:{match.group(1)}:{match.group(2)}:schema"

    match = re.match(
        r"document_types/([^/]+)/releases/([^/]+)/package\.yaml$",
        file_path
    )
    if match:
        return f"doctype:{match.group(1)}:{match.group(2)}:manifest"

    # Role prompts (both role: and fragment: formats)
    match = re.match(
        r"prompts/roles/([^/]+)/releases/([^/]+)/role\.prompt\.txt$",
        file_path
    )
    if match:
        return f"role:{match.group(1)}:{match.group(2)}:role_prompt"

    # Role meta.yaml
    match = re.match(
        r"prompts/roles/([^/]+)/releases/([^/]+)/meta\.yaml$",
        file_path
    )
    if match:
        return f"fragment:role:{match.group(1)}:{match.group(2)}:meta"

    # Templates
    match = re.match(
        r"prompts/templates/([^/]+)/releases/([^/]+)/template\.txt$",
        file_path
    )
    if match:
        return f"template:{match.group(1)}:{match.group(2)}:template"

    match = re.match(
        r"prompts/templates/([^/]+)/releases/([^/]+)/meta\.yaml$",
        file_path
    )
    if match:
        return f"template:{match.group(1)}:{match.group(2)}:meta"

    # Workflow definitions
    match = re.match(
        r"workflows/([^/]+)/releases/([^/]+)/definition\.json$",
        file_path
    )
    if match:
        return f"workflow:{match.group(1)}:{match.group(2)}:definition"

    # Standalone schemas
    match = re.match(
        r"schemas/([^/]+)/releases/([^/]+)/schema\.json$",
        file_path
    )
    if match:
        return f"schema:{match.group(1)}:{match.group(2)}:schema"

    return None
