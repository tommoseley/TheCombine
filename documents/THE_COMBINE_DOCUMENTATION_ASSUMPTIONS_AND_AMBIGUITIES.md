# The Combine Documentation — Assumptions & Ambiguities

**Document Type:** Documentation Audit  
**Status:** Reference  
**Version:** 1.0  
**Date:** December 2025  

---

This document surfaces assumptions, inferred behaviors, and future-implying language identified during the creation of The Combine's canonical documentation. These items are listed for awareness. No resolutions are proposed.

---

## 1. System Architecture & Database Documentation

### 1.1 Assumptions Made

1. **Staleness propagation mechanism** — The documentation states documents can become stale when inputs change, but the trigger or update logic that sets `is_stale = true` was not observed in the examined code. The mechanism is assumed to exist.

2. **`accepted_at`, `rejected_at`, `accepted_by`, `rejected_by`, `rejection_reason` columns** — These columns are referenced in ADR-007 and the DocumentStatusService, but their presence in the actual `documents` table was inferred from the service code, not directly observed in a schema definition.

3. **Single-tenant deployment** — Stated as assumption based on absence of observed multi-tenancy code, but not explicitly confirmed as an architectural constraint.

4. **`space_type` usage** — The documentation describes `space_type` as supporting "project | organization | team" but only "project" scope was observed in actual use. Organization and team scopes are assumed to exist as schema capabilities.

5. **Handler method signatures** — The `process()`, `render()`, `render_summary()`, and `transform()` methods are described as handler responsibilities, but only `process()` and `render()` were directly observed in code. `render_summary()` and `transform()` are inferred from the architecture design record.

### 1.2 Inferred Behavior Not Explicitly Supported

1. **Version lineage** — The documentation describes `is_latest` flag enabling version history, but the actual versioning workflow (how old versions are created, when `is_latest` is set to false) was not observed.

2. **Prompt caching** — Referenced in user memories but not observed in the examined code paths.

3. **`gating_rules` enforcement** — The column exists in `document_types` but no code was observed that evaluates gating rules beyond `required_inputs`.

4. **Schema validation strictness** — The documentation states "Validation is strict. A document that does not conform is rejected, not silently accepted." This behavior was inferred from the architecture design record, not observed in handler code.

### 1.3 Language Implying Future Intent

1. "Future types" in `RelationType` class — `REFERENCES`, `SUPERSEDES`, `CONSTRAINS` are listed as future relation types, implying roadmap.

2. The Document Relation model docstring mentions "references" and "supersedes" as "[future]".

---

## 2. UX Reference Documentation

### 2.1 Assumptions Made

1. **Activity panel (right pane)** — Described as "Reserved for future: status, history" based on the Design Manifesto's three-pane description, but no right panel was observed in current templates. This is an assumption that the panel exists but is empty.

2. **Acceptance button existence** — The documentation describes Accept and Request Changes buttons with enablement conditions, but these buttons were not observed in the examined templates. Their behavior is inferred from ADR-007.

3. **Rejection workflow** — The `rejected_at`, `rejected_by`, and `rejection_reason` fields are referenced, and subtitles like "Changes requested" are described, but the actual rejection UI flow was not observed.

4. **Export functionality** — Markdown and JSON export are described based on the complete_product_definition.md document, but export endpoints and UI were not observed in the current codebase. This may be a Phase 1 feature not yet implemented.

5. **Status summary counts in collapsed project row** — The template shows status icons with counts, but the actual `status_summary` data structure and its computation were not observed in the route or service code.

### 2.2 Inferred Behavior Not Explicitly Supported

1. **Accordion "only one project open" behavior** — The JavaScript implements this, but whether this is the intended permanent behavior or an implementation choice was not confirmed by specification.

2. **Disabled button visibility** — The statement "Disabled buttons remain visible but inactive. The UI does not hide actions that are temporarily unavailable" describes expected behavior but was not observed in templates (the Generate button enablement logic was not fully traced).

3. **Missing document display in expanded project** — The template contains hardcoded checks for specific doc_type_ids (`project_discovery`, `epic_backlog`, `technical_architecture`). This is fragile and may not reflect intended behavior for a registry-driven system.

4. **Streaming build emoji prefixes** — The documentation states "Status messages include emoji prefixes for quick scanning" based on observed `ProgressUpdate` messages, but whether these emojis are part of the design system or incidental was not confirmed.

### 2.3 Language Implying Future Intent

1. "Activity panel (Reserved for future: status, history)" — Explicitly references future functionality.

2. "Single-user workflows only (MVP)" — The "(MVP)" qualifier implies multi-user is planned.

3. "Export is one-way. The Combine does not import from external systems." — The present tense "does not" could imply this may change.

4. Section 6.4 "Where The System Intentionally Stops" uses present tense constraints that could be interpreted as current-state or permanent-state.

---

## 3. Cross-Document Ambiguities

1. **Handler naming inconsistency** — `technical_architecture` uses `ArchitectureSpecHandler`, suggesting the handler was originally named for `architecture_spec`. The documentation reflects the current state but the naming inconsistency suggests historical drift.

2. **Document type naming** — The database was updated to use `technical_architecture` but the handler class is still `ArchitectureSpecHandler`. The documentation reflects both but does not resolve whether this is intentional aliasing or incomplete migration.

3. **Epic-scope documents** — Both documents reference `scope = 'epic'` as a supported value, but no epic-scope document behavior was observed. It is unclear if this is implemented but unused, partially implemented, or documented but not built.

4. **`story_backlog` dependencies** — The documentation states `story_backlog` requires both `epic_backlog` and `technical_architecture`, but the database update described in conversation history suggests this was a recent change. The documentation reflects post-change state but does not capture whether this dependency chain is tested.

---

*These items are surfaced for awareness. No resolutions are proposed.*
