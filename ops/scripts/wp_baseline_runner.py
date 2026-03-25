#!/usr/bin/env python3
"""WP Baseline Replay Runner — Synthetic Dataset.

Generates Work Packages from 5 synthetic scenarios using the v1.1.0 prompt,
evaluates each with wp_defect_evaluator, and produces an aggregate report.

Usage:
    cd ~/dev/TheCombine
    python3 ops/scripts/wp_baseline_runner.py

Requires: ANTHROPIC_API_KEY in environment or .env
"""

import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.domain.services.wp_defect_evaluator import evaluate_wp
from app.domain.services.document_builder_pure import apply_post_processing


# ===========================================================================
# Synthetic Dataset — 5 scenarios with intentional variation
# ===========================================================================

SCENARIOS = [
    {
        "id": "WP-SIMPLE-001",
        "label": "Simple single-feature",
        "description": "Small scope, clear objective, one expected WS",
        "ip_candidates": [
            {
                "candidate_id": "WPC-001",
                "title": "User Authentication Module",
                "rationale": "The system requires basic username/password authentication before any other features can be used.",
                "scope_in": ["Login form", "Password hashing", "Session management"],
                "scope_out": ["OAuth integration", "Two-factor authentication"],
                "dependencies": [],
                "definition_of_done": ["Users can log in with username and password", "Sessions persist across page refreshes"],
            }
        ],
        "ta_summary": "Monolithic FastAPI application with PostgreSQL. Authentication uses bcrypt for password hashing and JWT for sessions. No external identity provider.",
        "ta_version_id": "TA-v1.0-auth-baseline",
        "adr_refs": ["ADR-010"],
        "policy_context": "POL-ADR-EXEC-001 governs all execution. POL-QA-001 requires test-first development.",
    },
    {
        "id": "WP-MODERATE-002",
        "label": "Moderate multi-WS",
        "description": "Medium scope, 3 expected WSs, clear dependencies",
        "ip_candidates": [
            {
                "candidate_id": "WPC-002",
                "title": "RESTful API Layer",
                "rationale": "Core API endpoints for CRUD operations on projects, documents, and users. Must be complete before frontend can consume.",
                "scope_in": ["Project CRUD endpoints", "Document CRUD endpoints", "User management endpoints", "Input validation", "Error handling"],
                "scope_out": ["WebSocket endpoints", "File upload", "Batch operations"],
                "dependencies": [{"wp_id": "user_authentication", "dependency_type": "must_complete_first", "notes": "Auth middleware required for all endpoints"}],
                "definition_of_done": ["All endpoints return correct status codes", "Input validation rejects malformed requests", "Integration tests pass for all routes"],
            }
        ],
        "ta_summary": "FastAPI with SQLAlchemy ORM. Three-layer architecture: router → service → repository. All endpoints behind JWT middleware. OpenAPI schema auto-generated.",
        "ta_version_id": "TA-v1.1-api-layer",
        "adr_refs": ["ADR-010", "ADR-040"],
        "policy_context": "POL-ADR-EXEC-001 governs execution. POL-CODE-001 requires reuse-first. POL-QA-001 requires bug-first testing.",
    },
    {
        "id": "WP-COMPLEX-003",
        "label": "Complex multi-phase",
        "description": "Large scope with infrastructure, migration, and feature work",
        "ip_candidates": [
            {
                "candidate_id": "WPC-003",
                "title": "Database Migration and Schema Evolution",
                "rationale": "Legacy SQLite database must be migrated to PostgreSQL with schema changes to support multi-tenancy, audit logging, and document versioning.",
                "scope_in": [
                    "Alembic migration framework setup",
                    "Schema redesign for multi-tenancy",
                    "Data migration scripts",
                    "Audit trail tables (ADR-010)",
                    "Document versioning with revision hash",
                    "Rollback procedures",
                ],
                "scope_out": ["Read replicas", "Sharding", "NoSQL alternatives"],
                "dependencies": [],
                "definition_of_done": [
                    "All existing data migrated without loss",
                    "Multi-tenant queries filter by tenant_id",
                    "Audit trail captures all mutations",
                    "Rollback tested and documented",
                ],
            }
        ],
        "ta_summary": "PostgreSQL on RDS. Alembic for migrations. Multi-tenancy via row-level security. Audit tables per ADR-010. Document model uses JSONB content with SHA-256 revision hashes. No SQLite in production.",
        "ta_version_id": "TA-v2.0-rds-migration",
        "adr_refs": ["ADR-009", "ADR-010", "ADR-055"],
        "policy_context": "POL-ADR-EXEC-001, POL-ARCH-001 (stateless execution, separation of concerns), POL-QA-001 (bug-first testing).",
    },
    {
        "id": "WP-AMBIGUOUS-004",
        "label": "Ambiguous requirements",
        "description": "Vague objective, minimal constraints — tests prompt robustness",
        "ip_candidates": [
            {
                "candidate_id": "WPC-004",
                "title": "Improve User Experience",
                "rationale": "Users have reported the interface is confusing. Need to make it better.",
                "scope_in": ["UI improvements"],
                "scope_out": [],
                "dependencies": [],
                "definition_of_done": ["Users report improved satisfaction"],
            }
        ],
        "ta_summary": "React SPA with Vite. Component library not specified. No design system currently in place.",
        "ta_version_id": "TA-v0.1-draft",
        "adr_refs": [],
        "policy_context": "POL-ADR-EXEC-001 governs execution.",
    },
    {
        "id": "WP-CONSTRAINED-005",
        "label": "Highly constrained",
        "description": "Explicit constraints, security-sensitive, governance-heavy",
        "ip_candidates": [
            {
                "candidate_id": "WPC-005",
                "title": "Secret Management and Governance Controls",
                "rationale": "System handles API keys, database credentials, and user tokens. Current implementation stores secrets in environment variables without rotation, audit, or access control. Must comply with SOC-2 Type II requirements.",
                "scope_in": [
                    "AWS Secrets Manager integration",
                    "Secret rotation automation",
                    "Access audit logging",
                    "Tier-0 secret detection gate",
                    "Credential injection at runtime only",
                ],
                "scope_out": [
                    "Hardware security modules (HSM)",
                    "Client-side encryption",
                    "Key ceremony procedures",
                ],
                "dependencies": [
                    {"wp_id": "database_migration", "dependency_type": "must_complete_first", "notes": "Audit tables required"},
                ],
                "definition_of_done": [
                    "No secrets in source code or environment variables",
                    "All secrets retrieved from Secrets Manager at runtime",
                    "Rotation triggers no downtime",
                    "Access audit trail for every secret read",
                    "Tier-0 gate blocks commits containing secret patterns",
                ],
            }
        ],
        "ta_summary": "AWS ECS Fargate deployment. Secrets in AWS Secrets Manager, injected via ECS task definition. No secrets in container images or .env files. Tier-0 secret detection runs pre-commit and in CI. GOV-SEC-T0-002 governs secret handling.",
        "ta_version_id": "TA-v1.5-security-hardened",
        "adr_refs": ["ADR-009", "ADR-010", "ADR-050"],
        "policy_context": "POL-ADR-EXEC-001, GOV-SEC-T0-002 (secrets handling), POL-QA-001 (bug-first testing), POL-ARCH-001 (stateless execution).",
    },
]


# ===========================================================================
# Prompt Assembly
# ===========================================================================

def load_prompts(task_version: str = None):
    """Load WP role and task prompts.

    Args:
        task_version: Explicit task prompt version (e.g., "1.1.1").
                     If None, uses active release.

    Uses importlib to bypass the circular import in app.domain.workflow.__init__.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "prompt_loader",
        str(Path(__file__).parent.parent.parent / "app" / "domain" / "workflow" / "prompt_loader.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    loader = mod.PromptLoader()
    role_prompt = loader.load_role("project_manager")

    if task_version:
        task_prompt = loader.load_task(f"prompt:task:work_package:{task_version}")
    else:
        task_prompt = loader.load_task("work_package")
    return role_prompt, task_prompt


def build_user_message(scenario: dict) -> str:
    """Assemble the user message from a scenario's IP + TA context."""
    parts = []
    parts.append("Create a Work Package.")
    parts.append("\nDocument purpose: Work Package derived from Implementation Plan candidates.")
    parts.append("\n\n--- Input Documents ---")

    # Implementation Plan context
    ip_content = {
        "plan_summary": {"overall_intent": scenario["description"]},
        "work_package_candidates": scenario["ip_candidates"],
    }
    parts.append(f"\n### implementation_plan:\n```json\n{json.dumps(ip_content, indent=2)}\n```")

    # Technical Architecture context
    ta_content = {
        "architecture_summary": {"summary": scenario["ta_summary"]},
        "ta_version_id": scenario["ta_version_id"],
        "governance_pins": {
            "adr_refs": scenario["adr_refs"],
            "policy_context": scenario["policy_context"],
        },
    }
    parts.append(f"\n### technical_architecture:\n```json\n{json.dumps(ta_content, indent=2)}\n```")

    parts.append("\n\nRemember: Output ONLY valid JSON matching the schema. No markdown, no prose.")
    return "\n".join(parts)


# ===========================================================================
# LLM Execution
# ===========================================================================

async def generate_wp(system_prompt: str, user_message: str) -> dict:
    """Call LLM and parse WP JSON output."""
    import httpx
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY") or _load_api_key(),
        timeout=httpx.Timeout(120.0, connect=10.0),
    )

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        temperature=0.7,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = response.content[0].text
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens

    # Parse JSON
    cleaned = re.sub(r'^```json\s*', '', raw.strip())
    cleaned = re.sub(r'\s*```$', '', cleaned)
    wp_data = json.loads(cleaned)

    return {
        "data": wp_data,
        "raw": raw,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


def _load_api_key() -> str:
    """Load API key from .env if not in environment."""
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("ANTHROPIC_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"')
    raise ValueError("ANTHROPIC_API_KEY not found in environment or .env")


# ===========================================================================
# Main Runner
# ===========================================================================

async def run_baseline():
    print("=" * 70)
    print("WP Baseline Runner — Synthetic Dataset")
    print(f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"Scenarios: {len(SCENARIOS)}")
    print("=" * 70)

    # Load prompts (accept version override via CLI arg)
    task_version = sys.argv[1] if len(sys.argv) > 1 else None
    role_prompt, task_prompt = load_prompts(task_version)
    system_prompt = f"{role_prompt}\n\n{task_prompt}"
    version_label = task_version or "active"
    print(f"\nPrompt loaded (task version: {version_label}): {len(system_prompt)} chars")

    results = []
    total_input_tokens = 0
    total_output_tokens = 0

    for i, scenario in enumerate(SCENARIOS):
        print(f"\n--- [{i+1}/{len(SCENARIOS)}] {scenario['id']}: {scenario['label']} ---")

        user_message = build_user_message(scenario)
        print(f"  User message: {len(user_message)} chars")

        try:
            result = await generate_wp(system_prompt, user_message)
            wp_data = result["data"]
            total_input_tokens += result["input_tokens"]
            total_output_tokens += result["output_tokens"]
            print(f"  LLM: {result['input_tokens']} in, {result['output_tokens']} out")

            # Apply post-processing (governance floor)
            apply_post_processing(wp_data, "work_package")

            # Evaluate
            report = evaluate_wp(wp_data)
            print(f"  Eval: {report.summary}")

            results.append({
                "scenario_id": scenario["id"],
                "label": scenario["label"],
                "wp_data": wp_data,
                "evaluation": {
                    "checks": report.checks,
                    "summary": report.summary,
                },
                "tokens": {
                    "input": result["input_tokens"],
                    "output": result["output_tokens"],
                },
                "error": None,
            })

        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({
                "scenario_id": scenario["id"],
                "label": scenario["label"],
                "wp_data": None,
                "evaluation": None,
                "tokens": {"input": 0, "output": 0},
                "error": str(e),
            })

    # Aggregate
    print("\n" + "=" * 70)
    print("AGGREGATE RESULTS")
    print("=" * 70)

    successful = [r for r in results if r["error"] is None]
    failed_runs = [r for r in results if r["error"] is not None]

    print(f"\nRuns: {len(results)} total, {len(successful)} successful, {len(failed_runs)} failed")
    print(f"Tokens: {total_input_tokens} in, {total_output_tokens} out")

    # Defect distribution
    check_counts = {}
    for r in successful:
        for check in r["evaluation"]["checks"]:
            cid = check["check_id"]
            status = check["status"]
            if cid not in check_counts:
                check_counts[cid] = {"pass": 0, "fail": 0, "advisory": 0, "not_evaluable": 0}
            check_counts[cid][status] = check_counts[cid].get(status, 0) + 1

    print(f"\nDefect Distribution (n={len(successful)}):")
    print(f"{'Check ID':<35} {'Pass':>5} {'Fail':>5} {'Adv':>5} {'N/E':>5} {'Fail%':>6}")
    print("-" * 70)
    for cid, counts in sorted(check_counts.items()):
        total = sum(counts.values())
        fail_pct = f"{counts['fail'] / total * 100:.0f}%" if total > 0 else "N/A"
        print(f"{cid:<35} {counts['pass']:>5} {counts['fail']:>5} {counts['advisory']:>5} {counts['not_evaluable']:>5} {fail_pct:>6}")

    # Average defects per WP
    total_defects = sum(r["evaluation"]["summary"]["failed"] for r in successful)
    avg_defects = total_defects / len(successful) if successful else 0
    print(f"\nAvg defects per WP: {avg_defects:.1f}")
    print(f"Total defects: {total_defects}")

    # Save full results
    output_path = Path(__file__).parent.parent.parent / "docs" / "audits" / "wp-baseline-v1.0.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump({
            "meta": {
                "date": datetime.now(timezone.utc).isoformat(),
                "scenario_count": len(SCENARIOS),
                "successful_runs": len(successful),
                "failed_runs": len(failed_runs),
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "prompt_version": version_label,
                "model": "claude-sonnet-4-20250514",
            },
            "results": results,
            "aggregate": {
                "check_distribution": check_counts,
                "avg_defects_per_wp": avg_defects,
                "total_defects": total_defects,
            },
        }, f, indent=2, default=str)
    print(f"\nFull results saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(run_baseline())
