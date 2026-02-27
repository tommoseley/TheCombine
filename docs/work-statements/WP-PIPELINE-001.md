# WP-PIPELINE-001: Pipeline Restructuring & Floor Redesign

## Status: Draft

## Governing References

- ADR-050 -- Work Statement Verification Constitution
- ADR-051 -- Work Package as Runtime Primitive
- ADR-052 -- Document Pipeline WP/WS Integration
- ADR-053 -- Planning Before Architecture in Software Product Development
- WP-DCW-001 -- Prior work that established WP/WS ontology (this WP corrects pipeline ordering and completes cleanup)

---

## Intent

Correct the production pipeline to enforce proper dependency ordering and eliminate architectural waste. WP-DCW-001 established the WP/WS ontology but left three problems:

1. **IPP and IPF are redundant.** Same role prompt, same inputs, no new user decisions (no PGC) between them. IPF adds nothing that IPP couldn't produce. Collapse into a single Implementation Plan (IP).

2. **Work Packages are created before Technical Architecture.** WPs are architectural consumers -- they must reference TA components to be scoped. Creating them from IPF before TA exists produces vague packages that require rework after TA.

3. **The floor UI wastes 70% of screen space.** A vertical node list uses 30% width; the rest is empty canvas. A master-detail layout (compact pipeline rail + content panel) uses space correctly and eliminates the need for separate "View Document" / "Enter Workbench" buttons. Click a node, content mounts.

Additionally, epic/feature/backlog references still contaminate the codebase (50+ app files, 34 test files, 7 legacy doc types in active_releases).

---

## Corrected Pipeline

```
Before:  Concierge -> PD -> IPP -> IPF(creates WPs) -> TA -> per_WP(WS)
After:   Concierge -> PD -> IP -> TA -> WB[WP -> WS]
```

Where:
- **IP** = single Implementation Plan (replaces IPP + IPF). Produces candidate WPs (advisory, read-only).
- **TA** = Technical Architecture (unchanged, but now feeds WP creation).
- **WB** = Work Binder. Not a document type -- a UI workspace (view mode). Portal node on floor, master-detail content shows workbench grid.
- **WP** = Work Packages created in WB, requiring TA as input. User clicks "Create WPs", LLM generates from IP candidates + TA bindings.
- **WS** = Work Statements created per WP. User clicks "Create WSs" on a governed WP.

Key principles:
- TA defines the technical ontology. WPs bind work to that ontology.
- Without TA, a WP is vague. With TA, a WP is scoped.
- WB is a container (UI mode), not a doc type. WP and WS are the governed artifacts.
- Candidate WPs live only in IP output. Promote copies into governed WP with provenance stamp.

---

## Scope In

- Collapse IPP + IPF into single IP (combine-config + app code + tests)
- Fix POW step ordering: PD -> IP -> TA -> WP creation (requires TA) -> WS decomposition
- Add WP creation as user-initiated step (execution_mode: manual) with TA as required input
- Redesign floor from full-canvas ReactFlow to master-detail layout
- Work Binder as last pipeline node, detail view shows workbench grid
- Node cards become compact selectors (no action buttons, click to mount content)
- Remove legacy epic/feature/backlog references from entire codebase
- Clean up active_releases.json (remove 7 legacy doc types, 10 legacy tasks, 2 legacy workflows)

## Scope Out

- LLM-assisted "Bind" button for WP-to-TA component binding (future WP)
- User-authored WPs (v2 feature)
- Design step in pipeline (added when UI requirements exist)
- Prompt content changes (audited and documented, executed in follow-up)
- WP/WS state machine UI affordances
- TA diagram type additions (tuning, not structure)

---

## Definition of Done

1. Single IP document type replaces IPP + IPF
2. POW step order: Concierge -> PD -> IP -> TA -> WP(manual, requires TA) -> WS(manual)
3. Floor uses master-detail layout: compact rail (left) + content panel (right)
4. WB node on floor, detail view shows workbench with "Create WPs" / "Create WSs" buttons
5. No runtime code references `primary_implementation_plan` as a document type
6. No runtime code references `epic`, `feature`, or `backlog_item` as document types
7. Legacy configs removed from active_releases.json
8. Tier 0 green
9. All existing tests updated or removed to match new structure

---

## Execution Order

1. **WS-PIPELINE-001** -- Pipeline Config & Doc Type Consolidation
   - Collapse IPP+IPF into IP in combine-config
   - Fix POW step ordering
   - Add execution_mode to POW steps (auto vs manual)
   - WP requires TA as input
   - Schema/prompt audit (document changes, flag prompt updates)

2. **WS-PIPELINE-002** -- Floor Layout Redesign
   - Master-detail layout replacing full-canvas ReactFlow
   - Compact pipeline rail (node = selector)
   - Content panel mounts document viewer or workbench
   - WB node as portal to workbench view
   - Routes: /project/:id/floor (default, first node selected)
   - Depends on WS-PIPELINE-001 (needs new pipeline structure)

3. **WS-PIPELINE-003** -- Legacy Ontology Cleanup
   - Remove epic/feature/backlog_item from app code (50+ files)
   - Remove from test code (34 files)
   - Remove legacy doc types, workflows, tasks, schemas from combine-config
   - Clean active_releases.json
   - Independent of WS-PIPELINE-002, depends on WS-PIPELINE-001

WS-001 must execute first. WS-002 and WS-003 can execute in parallel after WS-001.

---

## Tech Debt (Acknowledged)

| Item | Current Approach | Preferred Approach | When |
|------|------------------|--------------------|------|
| IP prompt content | Audit only, flag changes | Updated prompts reflecting merged IP scope | WS-PIPELINE-004 |
| WP-to-TA binding | Manual reference during promotion | LLM-assisted Bind button with override | Next WP |
| User-authored WPs | LLM-generated only | User can create WPs from scratch | v2 |
| epic_set_summary in IPP schema | Renamed to plan_summary | Already correct in new IP schema | WS-PIPELINE-001 |

---

_End of WP-PIPELINE-001_
