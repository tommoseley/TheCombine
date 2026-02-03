# Versioning Conventions

This document defines semantic versioning rules for configuration artifacts.

## Semver Format

All versions follow [Semantic Versioning 2.0.0](https://semver.org/):

```
MAJOR.MINOR.PATCH
```

**Examples:** `1.0.0`, `1.4.0`, `2.0.0`

## Version Bump Rules

### MAJOR Version

Increment MAJOR when making **breaking changes**:

| Change Type | Example |
|-------------|---------|
| Schema field removed | `unknowns` field deleted |
| Schema field renamed | `blocking_questions` → `blockers` |
| Schema field type changed | `string` → `array` |
| Required field added | New required `compliance_notes` field |
| Authority level changed | `descriptive` → `prescriptive` |
| Production mode changed | `generate` → `authorize` |
| Semantic meaning changed | Field now means something different |

**Rule:** Any change that could break existing documents or downstream consumers requires a MAJOR bump.

### MINOR Version

Increment MINOR for **backward-compatible additions**:

| Change Type | Example |
|-------------|---------|
| Optional field added | New optional `metadata` field |
| New docdef section | Additional sidecar section |
| Prompt refinement (same structure) | Clearer instructions, same output |
| New enum value added | `status` gains new valid value |
| Validation relaxed | Field was required, now optional |

**Rule:** Existing documents remain valid. New capabilities are additive.

### PATCH Version

Increment PATCH for **non-functional changes**:

| Change Type | Example |
|-------------|---------|
| Typo fixes | "recieve" → "receive" |
| Comment/documentation updates | Clarified field description |
| Whitespace/formatting | JSON reformatted |
| Prompt wording tweaks | Same meaning, better phrasing |

**Rule:** No semantic change. Existing behavior unchanged.

## Compatibility Gates

The following compatibility rules are **enforced by tooling**:

### Schema Compatibility

```
Schema breaking change → MAJOR bump required
```

Breaking changes include:
- Removing required fields
- Changing field types
- Renaming fields without aliases
- Adding required fields without defaults

### DocDef Pointer Resolution

```
DocDef source_pointer → MUST resolve to schema field
```

All `source_pointer` values in docdefs must reference valid schema paths for the same release.

### Cross-Artifact Consistency

Within a single release:
- Schema version = release version
- DocDef version = release version
- All internal references resolve

### Prompt-Schema Alignment

```
Prompt output instructions → MUST match schema structure
```

If a prompt says "output a `summary` field", the schema must define `summary`.

## Version Inheritance

When creating a new release:

1. **Start from latest released version**
2. **Apply changes**
3. **Determine bump type** (major/minor/patch)
4. **Increment appropriately**

```
Current: 1.4.0
Change: Added optional field
Bump: MINOR
New: 1.5.0
```

## Pre-release Versions

For work-in-progress, use pre-release suffixes:

```
1.5.0-alpha.1
1.5.0-beta.2
1.5.0-rc.1
```

Pre-release versions:
- Are not activatable in production
- May be used for preview/testing
- Do not appear in `active_releases.json`

## Version Lifecycle

```
Draft (uncommitted)
    ↓
Committed (e.g., 1.5.0)
    ↓
Staged (validated, frozen)
    ↓
Released (active pointer updated)
    ↓
Superseded (new version activated)
    ↓
Archived (optional cleanup)
```

Once a version is released:
- The release directory is **immutable**
- Fixes require a **new version**
- Rollback changes the **active pointer**, not the content

## Examples

### Breaking Schema Change

```yaml
# Before (1.4.0)
schema:
  required: [project_name, preliminary_summary]

# After - field removed
schema:
  required: [project_name]  # preliminary_summary removed

# Version: 2.0.0 (MAJOR)
```

### Additive Change

```yaml
# Before (1.4.0)
schema:
  properties:
    project_name: {type: string}

# After - optional field added
schema:
  properties:
    project_name: {type: string}
    metadata: {type: object}  # new, optional

# Version: 1.5.0 (MINOR)
```

### Documentation Fix

```yaml
# Before (1.4.0)
prompt: "Analize the requirements..."

# After - typo fixed
prompt: "Analyze the requirements..."

# Version: 1.4.1 (PATCH)
```
