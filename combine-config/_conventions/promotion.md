# Promotion Process

This document defines the release promotion workflow for configuration artifacts.

## Release States

| State | Git State | Editable | Production |
|-------|-----------|----------|------------|
| **Draft** | Uncommitted changes on branch | Yes | No |
| **Committed** | Committed to branch | No (new commit required) | No |
| **Staged** | Validated, ready for activation | No | No |
| **Released** | Active pointer updated | No | Yes |

## Promotion Flow

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   [Edit]  →  [Commit Draft]  →  [Stage Release]        │
│      ↑                              ↓                   │
│      │                        [Validation]              │
│      │                              ↓                   │
│      │                         Pass? ──No──→ [Fix]──┐  │
│      │                              │               │  │
│      └──────────────────────────────┼───────────────┘  │
│                                    Yes                  │
│                                     ↓                   │
│                            [Activate Release]          │
│                                     ↓                   │
│                              [Production]               │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Step 1: Edit (Draft State)

### Starting a Draft

1. Create or switch to an editing branch
2. Base the branch on the current active release
3. Make changes to artifacts

### Draft Rules

- Drafts are local/branch-scoped
- Multiple drafts may exist simultaneously
- Drafts have no effect on production
- Drafts may be abandoned without consequence

## Step 2: Commit Draft

### Commit Requirements

1. **Message required** - Describe what changed and why
2. **Version determined** - Based on change type (major/minor/patch)
3. **Manifest updated** - `package.yaml` reflects new version

### Commit Checklist

- [ ] All files saved
- [ ] Version number correct for change type
- [ ] `package.yaml` version matches directory
- [ ] Commit message is meaningful

### Git Operation

```bash
# Commit creates the release directory
git add document_types/project_discovery/releases/1.5.0/
git commit -m "feat(project_discovery): Add optional metadata field"
```

## Step 3: Stage Release

### Staging Validations

Before a release can be staged, it must pass:

| Validation | Description |
|------------|-------------|
| Schema validity | JSON Schema is syntactically valid |
| Reference resolution | All `source_pointer` values resolve |
| Cross-package deps | Required inputs have active releases |
| Prompt-schema alignment | Output instructions match schema |
| Authority-level rules | PGC present if required |
| Governance guardrails | No prohibited patterns |

### Staging Actions

1. Run full validation suite
2. Generate validation report
3. Lock the commit (no amendments)
4. Mark as "staged" in UI

### Staging Failures

If validation fails:
- Release cannot be staged
- Errors displayed inline
- Fix and re-commit required

## Step 4: Activate Release

### Activation Requirements

- Release must be staged (validated)
- User must have activation permission
- Cross-package compatibility confirmed

### Activation Actions

1. Update `_active/active_releases.json`
2. Commit the pointer change
3. Trigger runtime sync
4. Log activation event

### active_releases.json

```json
{
  "project_discovery": "1.5.0",
  "primary_implementation_plan": "1.0.0",
  "technical_architecture": "1.0.0",
  "implementation_plan": "1.0.0"
}
```

### Activation Commit

```bash
git add _active/active_releases.json
git commit -m "release: Activate project_discovery 1.5.0

Activated by: tom.moseley
Reason: Added optional metadata field for compliance tracking"
```

## Rollback

### Rollback Process

Rollback is achieved by changing the active pointer:

1. Identify previous working version
2. Update `active_releases.json`
3. Commit the change
4. Runtime syncs automatically

### Rollback Example

```json
// Before (broken)
{
  "project_discovery": "1.5.0"
}

// After (rollback)
{
  "project_discovery": "1.4.0"
}
```

```bash
git commit -m "rollback: Revert project_discovery to 1.4.0

Reason: Schema validation failures in production
Rolled back by: tom.moseley"
```

### Rollback Properties

- **Instant** - Pointer change only
- **Auditable** - Git history preserved
- **Reversible** - Can re-activate later
- **Non-destructive** - 1.5.0 still exists

## Tagging (Optional)

For significant releases, create Git tags:

```bash
git tag -a "project_discovery/v1.5.0" -m "Project Discovery 1.5.0"
git push origin "project_discovery/v1.5.0"
```

### Tag Format

```
{doc_type_id}/v{semver}
```

**Examples:**
- `project_discovery/v1.5.0`
- `technical_architecture/v2.0.0`

## Audit Trail

Every promotion action is recorded:

| Event | Recorded In |
|-------|-------------|
| Commit | Git commit history |
| Validation | Validation report (stored) |
| Activation | Git commit + DB audit log |
| Rollback | Git commit + DB audit log |

### Audit Metadata

Activation commits include:
- Acting user (logical identity)
- Timestamp (commit time)
- Reason (commit message)
- Previous version (diff context)

## Permissions (MVP)

| Action | Permission |
|--------|------------|
| Edit/Commit | Admin role |
| Stage | Admin role |
| Activate | Admin role |
| Rollback | Admin role |

Future: Role-based activation with approval workflows.

## Multi-Package Releases

When releasing changes that span multiple packages:

1. Commit all package changes
2. Stage each package
3. Update `active_releases.json` with all new versions
4. Single activation commit

```json
{
  "project_discovery": "1.5.0",
  "primary_implementation_plan": "1.1.0"
}
```

This ensures atomic activation of related changes.
