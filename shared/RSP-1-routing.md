📘 RSP-1.1 — Combine Routing Specification
Routing System for Artifact Identification, Context Loading, and Agent Handoff

Version: 1.1
Status: Final
Authors: Tom Moseley, ChatGPT
Reviewed by: Claude
Last Updated: 2025-12-09

🧭 Overview

The Combine requires a unified, deterministic addressing system for all engineering artifacts—epics, features, stories, ADRs, and beyond.
RSP-1 defines the canonical routing scheme used by:

Agents (PM → BA → Architect → Dev → QA)

The orchestrator

The artifact loader

The persistence layer (filesystem, DB, S3)

Breadcrumb-based resumability

This routing system is the Combine’s internal coordinate plane, equivalent to URLs on the web or ARNs in AWS.

🔖 1. Canonical Routing Format

All artifacts are addressed using a terse, fixed-structure path:

project_id / epic_id / feature_id / story_id


Each section is optional except project_id.

Example (full path)
HMP/E001/F003/S007

Example (epic only)
HMP/E001

Example (ADR)
HMP/AD-001


This format is LLM-friendly, unambiguous, and trivial to parse.

📚 2. Segment Definitions
Segment	Pattern	Example	Description
project_id	[A-Z0-9]{2,8}	HMP	Top-level initiative
epic_id	E\d{3}	E001	Major capability
feature_id	F\d{3}	F003	Vertical slice inside an epic
story_id	S\d{3}	S007	Implementable unit
adr_id	AD-\d{3}	AD-001	Architecture decision record
ADR Namespace

ADRs exist directly under the project root:

HMP/AD-001
HMP/AD-002


They are not nested under epics or features.

🧩 3. Grammar (Formal)
project      ::= UPPERCASE_ALPHANUM{2,8}
epic_id      ::= "E" DIGIT DIGIT DIGIT
feature_id   ::= "F" DIGIT DIGIT DIGIT
story_id     ::= "S" DIGIT DIGIT DIGIT
adr_id       ::= "AD-" DIGIT DIGIT DIGIT

route        ::= project ( "/" epic_id ( "/" feature_id ( "/" story_id )? )? )?
adr_route    ::= project "/" adr_id


This ensures total consistency and zero ambiguity.

🔍 4. Validation Rules
Full route regex:
^[A-Z0-9]{2,8}(/E\d{3}(/F\d{3}(/S\d{3})?)?)?$

ADR route regex:
^[A-Z0-9]{2,8}/AD-\d{3}$

Example Validator
def validate_route(path: str) -> bool:
    return (
        re.match(ROUTE_PATTERN, path) is not None or
        re.match(ADR_PATTERN, path) is not None
    )

🧱 5. Resolution Semantics (Critical)

Given a route:

HMP/E001/F003/S007


The orchestrator must load:

Level	Artifact
Story	S007
Feature	F003
Epic	E001
Project	HMP
ADRs	HMP/AD-*

This ancestry chain becomes the full context unit passed to agents.

Agents never need to ask where data lives — the route is the lookup key.

🛠 6. Expansion Rules (Internal)

Terse → Full ID mapping follows a predictable pattern.

Example

Short route:

HMP/E001/F003/S007


Expands to:

Epic:    HMP-001
Feature: HMP-001-F003
Story:   HMP-001-F003-S007

Expansion Function
def expand_path(terse: str) -> dict:
    proj, *rest = terse.split("/")
    epic, feature, story = (rest + [None]*3)[:3]

    expanded = {"project_id": proj}

    if epic:
        expanded["epic_id"] = f"{proj}-{epic[1:]}"
    if feature:
        expanded["feature_id"] = f"{expanded['epic_id']}-{feature}"
    if story:
        expanded["story_id"] = f"{expanded['feature_id']}-{story}"

    return expanded

💾 7. Storage Mapping (Filesystem, DB, S3)

The route is storage-agnostic.

Filesystem
workbench_data/HMP/E001/F003/S007.json

S3 / Blob storage
combine-artifacts/HMP/E001/F003/S007.json

Database
artifact_path = "HMP/E001/F003/S007"


This unifies local and distributed storage seamlessly.

🕒 8. Optional Version Suffix (Not yet required)

The routing format supports optional version tagging:

Version number
HMP/E001/F003/S007@v3

Point-in-time snapshot
HMP/E001/F003/S007@2024-12-09

Grammar extension
version_suffix ::= "@" ( "v" DIGITS | DATE )


This enables:

rollback

branching

experiment comparison

lineage tracking

🧭 9. Breadcrumb Schema (Minimal & Required)

Every agent must emit a breadcrumb object.

{
  "artifact_path": "HMP/E001/F003/S007",
  "intent": "Refined acceptance criteria.",
  "resume_instructions": "Architect should validate feasibility next.",
  "files": {
    "must_load": ["services/search/indexer.py"],
    "should_load": [],
    "search_hints": []
  }
}


This enables:

resumability

stateful handoffs

deterministic orchestration

context reconstruction

LLMs speak in routes, not raw artifacts.

🧰 10. Orchestrator Routing Engine (Implementation Contract)
10.1 Path Parsing
def resolve(path):
    parts = path.split("/")
    return (parts + [None]*4)[:4]

10.2 Artifact Loading
class ArtifactLoader:
    def load_with_context(self, path: str) -> dict:
        proj, epic, feat, story = resolve(path)

        return {
            "project": load_json(f"{proj}/project.json"),

            "epic": load_json(f"{proj}/{epic}/epic.json")
                if epic else None,

            "feature": load_json(f"{proj}/{epic}/{feat}/feature.json")
                if feat else None,

            "story": load_json(f"{proj}/{epic}/{feat}/{story}.json")
                if story else None,

            "adrs": load_glob(f"{proj}/AD-*.json")
        }


This guarantees every agent receives the full ancestry chain.

📁 11. Canonical Filesystem Structure Example
workbench_data/
  HMP/
    project.json
    AD-001.json
    AD-002.json
    E001/
      epic.json
      F001/
        feature.json
        S001.json
        S002.json
      F002/
        feature.json
        S003.json