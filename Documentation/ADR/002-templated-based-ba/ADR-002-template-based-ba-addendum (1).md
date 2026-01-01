# ADR-002: Template-Based BA Addendum Generation

**Status:** Accepted  
**Date:** 2025-12-01  
**Epic:** PIPELINE-001  
**Component:** Epic Processing Pipeline - BA Phase

---

## Context

The BA Phase of the Epic Processing Pipeline must generate a BA Addendum JSON for each Epic. The BA Addendum is complex, containing five distinct models:

1. **Proposal Quality Model** - Multi-dimensional quality scoring
2. **Test Coverage Model** - Tier-specific test requirements
3. **Ticket Complexity Tiers** - Simple/Medium/Complex classification
4. **Rework Communication Contract** - Developer Mentor feedback protocols
5. **Human Approval Rules** - Six risk categories requiring human review

### Requirements
- Every Epic must have a complete BA Addendum
- BA Addendum must be consistently structured and high-quality
- BA Phase must complete in <5 minutes
- BA Addendum should be customized to Epic characteristics (ideal, not MVP)

### Implementation Options

**Option 1: Template-Based Generation**
- Copy WORKFORCE-001-BA-ADDENDUM as template
- Customize only: epic_id, addendum_id, created_date, references
- Minimal per-Epic customization

**Option 2: Dynamic LLM-Based Generation**
- Use Claude to generate BA Addendum from Epic description
- Fully customized quality models for each Epic
- Requires prompt engineering, validation, error handling

**Option 3: Hybrid Approach**
- Start with template (MVP)
- Enhance with LLM customization (future iteration)
- Gradual migration path

---

## Decision

**Use template-based generation with minimal customization for MVP.**

The BA Phase will:
1. Load `workforce/canon/ba_addendum_template_v1.json`
2. Customize fields:
   - `epic_id`: Set to current Epic's ID
   - `addendum_id`: Generate as `{epic_id}-BA-ADDENDUM`
   - `created_date`: Set to current timestamp
   - `references.epic_id`: Update to current Epic
   - `references.canonical_architecture`: Update version if needed
3. Save customized addendum to `data/epics/{epic_id}/ba_addendum.json`
4. Add `ba_addendum_ref` to Epic JSON

**All quality models remain identical to WORKFORCE-001-BA-ADDENDUM template.**

---

## Rationale

### Why Template-Based for MVP?

**1. WORKFORCE-001-BA-ADDENDUM is High-Quality Reference**

The BA Addendum created for WORKFORCE-001 was:
- Carefully designed through PM → Architect → BA collaboration
- Validated against real-world workforce orchestration needs
- Contains proven quality models and approval rules
- Already comprehensive (5 models, 6 approval categories)

**Most Epics will have similar operational requirements:**
- Need quality scoring (proposal quality model)
- Need test coverage (test coverage model)
- Need complexity classification (simple/medium/complex)
- Need rework protocols (communication contract)
- Need human oversight (approval rules)

**2. Fast Execution (<10 seconds)**

```python
# Template-based generation is blazing fast
def generate_addendum(template: dict, epic: dict) -> dict:
    addendum = template.copy()
    addendum["epic_id"] = epic["epic_id"]
    addendum["addendum_id"] = f"{epic['epic_id']}-BA-ADDENDUM"
    addendum["created_date"] = datetime.utcnow().isoformat()
    # ... minimal customization ...
    return addendum
```

- No LLM calls (no network latency)
- No prompt engineering complexity
- No validation of LLM output
- Deterministic output

**3. Simple Implementation**

```python
class BAPhase(BasePhase):
    def execute(self, context: PipelineContext) -> PhaseResult:
        template = self.load_ba_addendum_template()
        customized = self.customize_ba_addendum(template, context.epic_json)
        self.save_ba_addendum(customized, context)
        context.epic_json["ba_addendum_ref"] = self.extract_ref(customized)
        return PhaseResult(success=True, phase_name=self.name)
```

- ~50 lines of code
- Easy to test
- No external dependencies
- Clear error handling

**4. Consistent Quality**

Template ensures:
- All Epics have complete BA Addendums (no missing models)
- Consistent structure (same JSON schema)
- Validated models (template is pre-validated)
- No LLM hallucinations or inconsistencies

**5. Meets MVP Goals**

PIPELINE-001 MVP goal: "Reduce Epic processing time from 2 hours to <10 minutes"

Template-based approach:
- ✅ Completes in <10 seconds (well under 5-minute timeout)
- ✅ Produces valid BA Addendum
- ✅ Enables automatic pipeline execution
- ✅ Simple enough to implement in Sprint 1

---

## Consequences

### Positive

✅ **Fast Execution**
- BA Phase completes in <10 seconds
- No risk of timeout
- Predictable performance

✅ **Consistent Quality**
- All BA Addendums have same structure
- No missing models or fields
- Pre-validated template

✅ **Simple Implementation**
- ~50 lines of code
- Easy to test and debug
- No external dependencies

✅ **Immediate Value**
- MVP delivers automation quickly
- Reduces Epic processing from 2 hours to <10 minutes
- Unblocks future enhancements

✅ **Clear Migration Path**
- Template provides baseline
- Future LLM enhancement can be additive
- Can A/B test template vs. LLM

### Negative

❌ **Less Customization Per Epic**

All Epics get same quality thresholds:
```json
{
  "proposal_quality_model": {
    "dimensions": {
      "technical_soundness": { "weight": 0.30, "min_score": 7 },
      "test_coverage": { "weight": 0.25, "min_score": 8 },
      // ... same for all Epics
    }
  }
}
```

Some Epics might benefit from custom thresholds:
- Simple CRUD Epics might need lower technical_soundness threshold
- Critical infrastructure Epics might need higher test_coverage threshold

**Mitigation:** Accept this limitation for MVP. Most Epics have similar quality requirements. Can add LLM customization in future iteration.

❌ **Manual Template Updates Needed**

If BA models evolve (e.g., new quality dimension added), must:
1. Update template manually
2. Regenerate BA Addendums for existing Epics (or accept version skew)

**Mitigation:** Version BA Addendum template (`v1`, `v1.1`, `v2`). Pipeline supports multiple template versions. Document template update process.

❌ **Template Might Not Fit Novel Epic Types**

Future Epic types might need fundamentally different BA models:
- ML/AI Epics: Need model performance metrics
- Data Pipeline Epics: Need data quality metrics
- Security Epics: Need threat modeling requirements

**Mitigation:** For MVP, support "standard" Epic types only (backend features, workflows). Document that novel Epic types require manual BA Addendum creation until templates are available.

### Risks and Mitigations

**Risk 1: Template Becomes Outdated**
- BA models evolve but template not updated
- **Mitigation:** Version template explicitly. Add template review to Epic retrospectives. Create template update process documentation.

**Risk 2: Epic-Specific Customization Needed**
- PM identifies Epic that needs custom quality thresholds
- **Mitigation:** Support manual BA Addendum editing. Pipeline can accept pre-existing BA Addendum (skip generation). Document override process.

**Risk 3: Template Quality Issues Propagate**
- Bug in template affects all Epics
- **Mitigation:** Validate template against schema before using. Add template regression tests. Version templates for rollback capability.

---

## Implementation Notes

### Template Structure

```
workforce/canon/ba_addendum_template_v1.json
```

Contains:
- Complete BA Addendum structure from WORKFORCE-001
- Placeholder values for epic_id, addendum_id, dates
- All five models with proven thresholds and rules

### Customization Logic

```python
def customize_ba_addendum(
    template: dict,
    epic_json: dict,
) -> dict:
    """Customize BA Addendum template for Epic."""
    addendum = template.copy()
    
    # Update identifiers
    addendum["epic_id"] = epic_json["epic_id"]
    addendum["addendum_id"] = f"{epic_json['epic_id']}-BA-ADDENDUM"
    addendum["version"] = "1.0"
    
    # Update timestamps
    addendum["created_date"] = datetime.utcnow().isoformat()
    addendum["updated_date"] = datetime.utcnow().isoformat()
    
    # Update references
    addendum["references"]["epic_id"] = epic_json["epic_id"]
    addendum["references"]["epic_version"] = epic_json["version"]
    
    # Architecture reference (if available)
    if "canonical_architecture_ref" in epic_json:
        arch_ref = epic_json["canonical_architecture_ref"]
        addendum["references"]["canonical_architecture"] = {
            "architecture_id": arch_ref["architecture_id"],
            "version": arch_ref["version"],
        }
    
    return addendum
```

### Validation

```python
# Validate template before use
from workforce.utils.schema_validator import validate_ba_addendum

template = load_ba_addendum_template()
validate_ba_addendum(template)  # Ensures template is valid
```

### Testing Strategy

```python
def test_ba_phase_generates_valid_addendum():
    """BA Phase produces valid BA Addendum from template."""
    template = load_ba_addendum_template_v1()
    epic = load_valid_epic_v1()
    
    ba_phase = BAPhase()
    result = ba_phase.execute(PipelineContext(epic_id="TEST-001", epic_json=epic))
    
    assert result.success
    assert "ba_addendum_ref" in epic
    
    # Load generated addendum
    addendum = load_ba_addendum(epic_dir("TEST-001") / "ba_addendum.json")
    
    # Validate structure
    validate_ba_addendum(addendum)
    
    # Verify customization
    assert addendum["epic_id"] == "TEST-001"
    assert addendum["addendum_id"] == "TEST-001-BA-ADDENDUM"
```

---

## Future Enhancement: LLM-Driven Customization

### When to Add LLM Generation

Consider LLM-based customization when:

1. **Epic Volume Increases (>50 Epics processed)**
   - Enough data to evaluate template effectiveness
   - Can measure how many Epics need custom thresholds

2. **Epic Type Diversity Increases**
   - Novel Epic types emerge (ML, data pipelines, security)
   - Template doesn't fit new Epic types

3. **PM Feedback Indicates Need**
   - Multiple Epics require manual BA Addendum editing
   - PMs request Epic-specific quality customization

### Potential Enhancement Design

```python
class BAPhase(BasePhase):
    def execute(self, context: PipelineContext) -> PhaseResult:
        if self.use_llm_customization:
            return self._generate_with_llm(context)
        else:
            return self._generate_from_template(context)
    
    def _generate_with_llm(self, context: PipelineContext) -> PhaseResult:
        """Use Claude to customize BA Addendum."""
        template = self.load_ba_addendum_template()
        
        prompt = f"""
        Given this Epic:
        {json.dumps(context.epic_json, indent=2)}
        
        And this BA Addendum template:
        {json.dumps(template, indent=2)}
        
        Customize the quality thresholds and approval rules for this specific Epic.
        Consider:
        - Epic complexity (simple/medium/complex)
        - Risk level (architectural changes, data handling, security)
        - Test requirements (integration vs. unit test focus)
        
        Return customized BA Addendum JSON.
        """
        
        response = call_claude_api(prompt)
        customized_addendum = parse_json(response)
        validate_ba_addendum(customized_addendum)
        
        return PhaseResult(success=True, artifacts={"ba_addendum": customized_addendum})
```

**Don't implement this until data justifies the complexity.**

---

## Related Decisions

- **ADR-001:** Pipeline Synchronous Execution (template-based keeps BA phase fast)
- **ADR-003:** File-Based Artifact Persistence (template stored in canon/, customized in epics/)
- **ADR-004:** Centralized Configuration (template path via config.canonical_path())

---

## References

- Epic PIPELINE-001: Story PIPELINE-104 (BA Phase - Addendum Generation)
- WORKFORCE-001-BA-ADDENDUM: Reference template with proven quality models
- Canonical Architecture v1.4: BA Phase specification

---

**Approved By:** Architect, Product Manager, Business Analyst  
**Review Date:** 2025-12-01  
**Next Review:** After processing 50 Epics or 6 months, whichever comes first
