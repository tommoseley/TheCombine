#!/usr/bin/env python3
"""
Registry Integrity Check -- Tier-0 gate.

Verifies every entry in active_releases.json resolves to an existing
artifact at its canonical global path. Missing asset = HARD_STOP.

Exit codes:
  0 = all assets present and valid
  1 = one or more assets missing or invalid
"""

import json
import sys
from pathlib import Path

# Resolve combine-config root relative to this script
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
CONFIG_ROOT = REPO_ROOT / "combine-config"
ACTIVE_RELEASES = CONFIG_ROOT / "_active" / "active_releases.json"


def check_file_exists(path: Path) -> str:
    """Return 'PASS' if file exists and is non-empty, else failure reason."""
    if not path.exists():
        return f"not found: {path.relative_to(REPO_ROOT)}"
    if path.stat().st_size == 0:
        return f"empty file: {path.relative_to(REPO_ROOT)}"
    return "PASS"


def check_json_valid(path: Path) -> str:
    """Return 'PASS' if file is valid JSON, else failure reason."""
    exists = check_file_exists(path)
    if exists != "PASS":
        return exists
    try:
        with open(path, "r", encoding="utf-8") as f:
            json.load(f)
        return "PASS"
    except json.JSONDecodeError as e:
        return f"invalid JSON: {e}"


def check_yaml_valid(path: Path) -> str:
    """Return 'PASS' if file is valid YAML, else failure reason."""
    exists = check_file_exists(path)
    if exists != "PASS":
        return exists
    try:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            yaml.safe_load(f)
        return "PASS"
    except Exception as e:
        return f"invalid YAML: {e}"


def main():
    if not ACTIVE_RELEASES.exists():
        print(f"FATAL: {ACTIVE_RELEASES} not found")
        return 1

    with open(ACTIVE_RELEASES, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = []
    pass_count = 0
    fail_count = 0

    # ---- document_types ----
    doc_types = data.get("document_types", {})
    for dt_id, version in doc_types.items():
        pkg_path = CONFIG_ROOT / "document_types" / dt_id / "releases" / version / "package.yaml"
        status = check_yaml_valid(pkg_path)
        label = f"document_types/{dt_id}:{version}"
        results.append((label, status))

    # ---- tasks ----
    tasks = data.get("tasks", {})
    for task_id, version in tasks.items():
        prompt_path = CONFIG_ROOT / "prompts" / "tasks" / task_id / "releases" / version / "task.prompt.txt"
        status = check_file_exists(prompt_path)
        label = f"tasks/{task_id}:{version}"
        results.append((label, status))

    # ---- schemas ----
    schemas = data.get("schemas", {})
    for schema_id, version in schemas.items():
        schema_path = CONFIG_ROOT / "schemas" / schema_id / "releases" / version / "schema.json"
        status = check_json_valid(schema_path)
        label = f"schemas/{schema_id}:{version}"
        results.append((label, status))

    # ---- roles ----
    roles = data.get("roles", {})
    for role_id, version in roles.items():
        role_path = CONFIG_ROOT / "prompts" / "roles" / role_id / "releases" / version / "role.prompt.txt"
        status = check_file_exists(role_path)
        label = f"roles/{role_id}:{version}"
        results.append((label, status))

    # ---- workflows ----
    workflows = data.get("workflows", {})
    for wf_id, version in workflows.items():
        defn_path = CONFIG_ROOT / "workflows" / wf_id / "releases" / version / "definition.json"
        status = check_json_valid(defn_path)
        label = f"workflows/{wf_id}:{version}"
        results.append((label, status))

    # ---- Print results ----
    print("=== Registry Integrity Check ===")
    for label, status in sorted(results):
        if status == "PASS":
            pass_count += 1
            print(f"  {label:<55s} PASS")
        else:
            fail_count += 1
            print(f"  {label:<55s} FAIL ({status})")

    total = pass_count + fail_count
    print()
    if fail_count == 0:
        print(f"RESULT: ALL {total} ASSETS VERIFIED")
        return 0
    else:
        print(f"RESULT: FAILED ({fail_count} of {total} assets missing or invalid)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
