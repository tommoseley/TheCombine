# WS-ADR-034-DISCOVERY: Project Discovery DocDef Migration

| | |
|---|---|
| **Work Statement** | WS-ADR-034-DISCOVERY |
| **Title** | Project Discovery DocDef Migration (First Real Document) |
| **Related ADRs** | ADR-034, ADR-034-B |
| **Predecessor** | WS-ADR-034-EXP3 |
| **Status** | Complete |
| **Expected Scope** | Medium (multi-commit) |
| **Owner** | Tom |
| **Created** | 2026-01-08 |

---

## Purpose

Migrate the existing `project_discovery` document type to the ADR-034 document composition system. This establishes the repeatable migration pattern for all future document types.

---

## Step 1: Section Inventory

### Current Handler Structure

From `project_discovery_handler.py`, the document contains:

| Section | Current Data Shape | Sample |
|---------|-------------------|--------|
| `project_name` | `string` | `"The Combine"` |
| `preliminary_summary` | `{problem_understanding, architectural_intent, scope_pressure_points}` | Object with 3 text fields |
| `unknowns` | `[{question, why_it_matters, impact_if_unresolved}]` | Array of unknown items |
| `stakeholder_questions` | `[{question, directed_to, blocking}]` | Array of questions |
| `early_decision_points` | `[{decision_area, why_early, options[], recommendation_direction}]` | Array of decisions |
| `known_constraints` | `[string]` | Simple string array |
| `assumptions` | `[string]` | Simple string array |
| `identified_risks` | `[{description, likelihood, impact_on_planning}]` | Array of risks |
| `mvp_guardrails` | `[string]` | Simple string array |
| `recommendations_for_pm` | `[string]` | Simple string array |

---

## Step 2: Archetype Mapping

| Section | Archetype | Component Strategy |
|---------|-----------|-------------------|
| `project_name` | Title (not a section) | Part of document header, not a rendered section |
| `preliminary_summary` | **Paragraph** | New: `SummaryBlockV1` or 3x `ParagraphV1` |
| `unknowns` | **Container** | New: `UnknownV1` + `UnknownsBlockV1` |
| `stakeholder_questions` | **Container** | Reuse: `OpenQuestionV1` fits (blocking + why_it_matters) |
| `early_decision_points` | **Container** | New: `DecisionPointV1` + `DecisionPointsBlockV1` |
| `known_constraints` | **List** | New: `StringListBlockV1` (generic) |
| `assumptions` | **List** | Reuse: `StringListBlockV1` |
| `identified_risks` | **Container** | New: `RiskV1` + `RisksBlockV1` |
| `mvp_guardrails` | **List** | Reuse: `StringListBlockV1` |
| `recommendations_for_pm` | **List** | Reuse: `StringListBlockV1` |

---

## Step 3: Components to Create

### New Schemas (6)

| Schema ID | Kind | Notes |
|-----------|------|-------|
| `schema:SummaryBlockV1` | type | Multi-field paragraph block |
| `schema:UnknownV1` | type | Item: question, why_it_matters, impact_if_unresolved |
| `schema:UnknownsBlockV1` | type | Container for UnknownV1[] |
| `schema:DecisionPointV1` | type | Item: decision_area, why_early, options[], recommendation |
| `schema:DecisionPointsBlockV1` | type | Container for DecisionPointV1[] |
| `schema:RiskV1` | type | Item: description, likelihood, impact |
| `schema:RisksBlockV1` | type | Container for RiskV1[] |
| `schema:StringListBlockV1` | type | Container for string[] with optional title |

### New Components (8)

| Component ID | Maps To |
|--------------|---------|
| `component:SummaryBlockV1:1.0.0` | schema:SummaryBlockV1 |
| `component:UnknownV1:1.0.0` | schema:UnknownV1 |
| `component:UnknownsBlockV1:1.0.0` | schema:UnknownsBlockV1 |
| `component:DecisionPointV1:1.0.0` | schema:DecisionPointV1 |
| `component:DecisionPointsBlockV1:1.0.0` | schema:DecisionPointsBlockV1 |
| `component:RiskV1:1.0.0` | schema:RiskV1 |
| `component:RisksBlockV1:1.0.0` | schema:RisksBlockV1 |
| `component:StringListBlockV1:1.0.0` | schema:StringListBlockV1 |

### Reuse Existing

| Existing | Reuse For |
|----------|-----------|
| `OpenQuestionV1` + `OpenQuestionsBlockV1` | `stakeholder_questions` (fields compatible) |

---

## Step 4: DocDef Structure

```python
docdef:ProjectDiscovery:1.0.0 = {
    "sections": [
        # Summary (paragraph block, no repeat)
        {"section_id": "summary", "shape": "single", "source_pointer": "/preliminary_summary", "component_id": "component:SummaryBlockV1:1.0.0"},
        
        # Unknowns (container, no repeat)
        {"section_id": "unknowns", "shape": "container", "source_pointer": "/unknowns", "component_id": "component:UnknownsBlockV1:1.0.0"},
        
        # Stakeholder Questions (container, no repeat) - reuse OpenQuestionsBlock
        {"section_id": "stakeholder_questions", "shape": "container", "source_pointer": "/stakeholder_questions", "component_id": "component:OpenQuestionsBlockV1:1.0.0"},
        
        # Decision Points (container, no repeat)
        {"section_id": "decision_points", "shape": "container", "source_pointer": "/early_decision_points", "component_id": "component:DecisionPointsBlockV1:1.0.0"},
        
        # Constraints (string list, no repeat)
        {"section_id": "constraints", "shape": "single", "source_pointer": "/known_constraints", "component_id": "component:StringListBlockV1:1.0.0", "context": {"title": "Known Constraints"}},
        
        # Assumptions (string list, no repeat)
        {"section_id": "assumptions", "shape": "single", "source_pointer": "/assumptions", "component_id": "component:StringListBlockV1:1.0.0", "context": {"title": "Assumptions"}},
        
        # Risks (container, no repeat)
        {"section_id": "risks", "shape": "container", "source_pointer": "/identified_risks", "component_id": "component:RisksBlockV1:1.0.0"},
        
        # Guardrails (string list, no repeat)
        {"section_id": "guardrails", "shape": "single", "source_pointer": "/mvp_guardrails", "component_id": "component:StringListBlockV1:1.0.0", "context": {"title": "MVP Guardrails"}},
        
        # Recommendations (string list, no repeat)
        {"section_id": "recommendations", "shape": "single", "source_pointer": "/recommendations_for_pm", "component_id": "component:StringListBlockV1:1.0.0", "context": {"title": "Recommendations for PM"}},
    ]
}
```

---

## Step 5: Acceptance Criteria

1. All new schemas seeded and accepted
2. All new components seeded with generation guidance and fragment bindings
3. All new fragments render correctly
4. `docdef:ProjectDiscovery:1.0.0` exists
5. Preview endpoints return correct blocks for sample payload
6. No HTML in JSON responses
7. Full test suite passes
8. Migration checklist documented

---

## Step 6: Migration Checklist (Template)

This checklist will be refined as we execute:

```markdown
## Document Migration Checklist

### 1. Inventory
- [ ] List all sections from existing handler
- [ ] Document current data shapes
- [ ] Identify sample payload

### 2. Map to Archetypes
- [ ] Classify each section: Paragraph, List, Container
- [ ] Identify reusable components
- [ ] Identify new components needed

### 3. Create Schemas
- [ ] Add item schemas (XxxV1)
- [ ] Add container schemas (XxxBlockV1)
- [ ] Update schema count test

### 4. Create Components
- [ ] Add components with generation guidance
- [ ] Add fragment aliases to registry

### 5. Create Fragments
- [ ] Add item fragments
- [ ] Add container fragments

### 6. Create DocDef
- [ ] Define sections with pointers
- [ ] Set correct shapes
- [ ] Map to components

### 7. Test
- [ ] Unit tests for new schemas
- [ ] Integration tests for docdef
- [ ] Preview endpoint verification

### 8. Document
- [ ] Update work statement with findings
- [ ] Capture reusable patterns
```

---

## Findings

### Components Created

| Type | ID | Purpose |
|------|-----|---------|
| Schema | `schema:StringListBlockV1` | Generic string list container |
| Schema | `schema:SummaryBlockV1` | Multi-field paragraph block |
| Schema | `schema:RisksBlockV1` | Risk item container |
| Component | `component:StringListBlockV1:1.0.0` | Reusable across 4 sections |
| Component | `component:SummaryBlockV1:1.0.0` | Document header summaries |
| Component | `component:RisksBlockV1:1.0.0` | Risk rendering |
| Fragment | `StringListBlockV1Fragment` | Handles bullet/numbered/check styles |
| Fragment | `SummaryBlockV1Fragment` | Blue-tinted summary box |
| Fragment | `RisksBlockV1Fragment` | Likelihood-colored risk cards |
| DocDef | `docdef:ProjectDiscovery:1.0.0` | First real document migration |

### Reuse Patterns Identified

1. **StringListBlockV1** covers any `string[]` section — constraints, assumptions, guardrails, recommendations all use the same component
2. **Context passthrough** for static titles — docdef `context: {"title": "..."}` flows to fragment without repeat_over
3. **Style variants** via context — `{"style": "check"}` renders checkmarks instead of bullets

### Builder Enhancement

Fixed: Simple containers (no `repeat_over`) now receive static context from section config.

### Migration Checklist Validated

The checklist in this document proved accurate. Ready for reuse on next document type.

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-08 | Initial inventory and mapping |

---

*End of Work Statement*

