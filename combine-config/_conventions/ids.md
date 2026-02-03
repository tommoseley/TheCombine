# ID Conventions

This document defines canonical identifier formats for all configuration artifacts.

## Document Type IDs

**Format:** `snake_case`

**Examples:**
- `project_discovery`
- `primary_implementation_plan`
- `technical_architecture`
- `implementation_plan`
- `epic`
- `feature`

**Rules:**
- Lowercase only
- Underscores for word separation
- No version suffix (version is directory-based)
- Must be unique across all document types

## Artifact IDs

Artifact IDs are URN-style identifiers used for cross-referencing.

### Prompt Artifacts

| Type | Format | Example |
|------|--------|---------|
| Role prompt | `prompt:role:{role_id}:{semver}` | `prompt:role:technical_architect:1.0.0` |
| Task prompt | `prompt:{doc_type_id}:task:{semver}` | `prompt:project_discovery:task:1.4.0` |
| QA prompt | `prompt:{doc_type_id}:qa:{semver}` | `prompt:project_discovery:qa:1.1.0` |
| PGC context | `prompt:{doc_type_id}:pgc:{semver}` | `prompt:project_discovery:pgc:1.0.0` |
| Questions | `prompt:{doc_type_id}:questions:{semver}` | `prompt:project_discovery:questions:1.0.0` |
| Template | `prompt:template:{template_id}:{semver}` | `prompt:template:document_generator:1.0.0` |

### Schema Artifacts

**Format:** `schema:{doc_type_id}:{semver}`

**Example:** `schema:project_discovery:1.4.0`

### DocDef Artifacts

**Format:** `docdef:{doc_type_id}:{surface}:{semver}`

Where `surface` ∈ {`full`, `sidecar`}

**Examples:**
- `docdef:project_discovery:full:1.4.0`
- `docdef:project_discovery:sidecar:1.4.0`

### Rule Artifacts

**Format:** `rules:{doc_type_id}:{semver}`

**Example:** `rules:epic:1.0.0`

### Workflow Artifacts

**Format:** `workflow:{workflow_id}:{semver}`

**Example:** `workflow:software_product_development:1.0.0`

### Component Artifacts

**Format:** `component:{component_id}:{semver}`

**Example:** `component:SummaryBlockV1:1.0.0`

## Role IDs

**Format:** `snake_case`

**Examples:**
- `technical_architect`
- `project_manager`
- `business_analyst`
- `developer`
- `quality_assurance`

## Template IDs

**Format:** `snake_case`

**Examples:**
- `document_generator`
- `qa_validator`

## Directory Naming

Directories use the same ID format as their contents:

```
document_types/
  project_discovery/          ← doc_type_id
    releases/
      1.4.0/                   ← semver

prompts/
  roles/
    technical_architect/      ← role_id
      releases/
        1.0.0/                 ← semver
```

## Filename Conventions

Within a release directory, filenames are fixed:

| Artifact | Filename |
|----------|----------|
| Package manifest | `package.yaml` |
| Role prompt | `role.prompt.txt` |
| Task prompt | `task.prompt.txt` |
| QA prompt | `qa.prompt.txt` |
| PGC context | `pgc_context.prompt.txt` |
| Questions prompt | `questions.prompt.txt` |
| Output schema | `output.schema.json` |
| Full docdef | `full.docdef.json` |
| Sidecar docdef | `sidecar.docdef.json` |
| Gating rules | `gating.rules.json` |
| Workflow fragment | `workflow.fragment.json` |
| Template | `template.txt` |

This ensures:
- Deterministic resolution
- Diff-friendly reviews
- No version confusion within a release
