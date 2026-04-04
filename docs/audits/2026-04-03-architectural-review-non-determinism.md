# Architectural Review: Non-Determinism and the Generation/Selection Boundary

**Date:** 2026-04-03
**Author:** Tom Moseley, with Claude (Opus 4.6)
**Trigger:** MSA-001 binder quality review findings
**Status:** Active finding — informs future design decisions

---

## Executive Summary

The Combine's design hypothesis was that industrial manufacturing principles — stations, quality gates, governance, explicit procedures — could make AI-driven knowledge work deterministic and reliable. After eight months of development and the MSA-001 binder review, we have identified a boundary condition in this hypothesis: **governance can control selection of outputs but cannot control generation of outputs.** The system was over-indexed on making generation reliable when it should have been designed around making selection rigorous and learning accumulative.

This is not a failure of the system. It is a discovery of where industrial principles apply (selection, constraint, accumulation) and where they do not (LLM behavior).

---

## The Original Hypothesis

The Combine was designed around an implicit assumption:

> If we apply enough structure — role prompts, task prompts, schemas, quality gates, governance pins, lineage tracking — LLM output will converge toward correctness.

This assumption informed every major design decision:

- **ADR-040 (Stateless Execution):** Each LLM invocation receives structured context, not transcripts. Continuity comes from mechanical state, not memory.
- **ADR-049 (No Black Boxes):** Every workflow is explicitly composed of gates, passes, and mechanical operations.
- **ADR-064 (Durable Authority):** PGC answers persist as project-level governed inputs across pipeline rewinds.
- **POL-WS-001 (Standard Work Statements):** Work is defined with explicit procedures, verification criteria, and containment boundaries.

These are good engineering decisions. They remain valid. But they were built on an unstated premise: that the LLM, given the right inputs, would produce the right outputs reliably enough that governance would only need to catch edge cases.

---

## What MSA-001 Revealed

The MSA-001 binder review produced five findings, three rated High severity:

| # | Severity | Finding | Error Type |
|---|----------|---------|------------|
| 1 | High | WS schema non-compliance — missing POL-WS-001 required fields | Structural |
| 2 | High | Hybrid AI gap — cloud-only implementation despite hybrid TA | Semantic |
| 3 | High | Duplicate scope — WS-069/WS-070 vs WS-074/WS-075 overlap | Semantic |
| 4 | Medium | Missing search baseline — WS-081 assumes non-existent controller | Semantic |
| 5 | Medium | Siri vs Speech Framework inconsistency across documents | Semantic |

**Finding 1** was a platform defect: the WS output schema did not include fields that POL-WS-001 requires. The LLM was never asked to generate these fields. This was fixed by bumping the schema to v1.2.0 and adding the fields to both task prompts. This is a genuine mechanical fix — the system can never produce this class of error again.

**Findings 2-5** are semantic errors in LLM-generated content. The TA said "hybrid AI" but the WSs only implemented cloud. Two WPs produced overlapping WSs. A WS assumed a prerequisite that no other WS creates. The TA said "Siri" but the WSs said "SFSpeechRecognizer."

These are not edge cases caught by quality gates. These are the primary output of the system being wrong in ways that only human review detected.

---

## The Dice Problem

The current iteration loop when output is wrong:

1. Generate (stateless LLM invocation)
2. QA gate evaluates (another stateless LLM invocation)
3. If QA passes, accept. If QA fails, remediate (another LLM invocation).
4. Operator reviews binder. Finds problems.
5. Operator rewinds with correction brief (ADR-069).
6. Pipeline regenerates (stateless LLM invocation — no memory of prior attempt).
7. Operator reviews again.

This loop has a structural problem: **nothing learns.** Per ADR-040, every LLM invocation starts fresh. The correction brief (ADR-069) injects new information as prompt text, but the LLM does not know it failed before, does not know what was wrong, and may or may not interpret the correction as intended.

This is rejection sampling, not iteration. The system re-rolls until it gets an acceptable output, then calls the result "correct." But:

- The LLM did not converge toward the answer.
- The process did not become more reliable.
- The same error can recur on the next project.

The manufacturing analogy breaks down here. In a factory, a machine tool cuts to specification every time. Quality gates catch defects from material variance or tool wear. The process itself is deterministic. In The Combine, the "machine tool" is fundamentally stochastic. Quality gates are not catching rare defects — they are filtering a random process.

---

## The Boundary: Generation vs Selection

The hypothesis was not entirely wrong. It was applied to the wrong layer.

**Where industrial principles work (selection and constraint):**

| Mechanism | What It Does | Deterministic? |
|-----------|-------------|----------------|
| JSON Schema validation | Rejects structurally invalid output | Yes |
| IA contract enforcement | Rejects output missing required sections | Yes |
| Lineage tracking | Records what produced what | Yes |
| Authority records | Preserves operator decisions across rewinds | Yes |
| Governance pins | Traces execution to architectural decisions | Yes |
| Tier 0 verification | Validates scope containment | Yes |

These are genuinely deterministic. They add real value. They should be preserved and strengthened.

**Where industrial principles do not work (generation):**

| Mechanism | What It Attempts | Deterministic? |
|-----------|-----------------|----------------|
| Role prompts | Shape LLM persona | No — soft influence |
| Task prompts | Direct LLM output | No — soft influence |
| Correction briefs | Steer regeneration | No — prompt-level suggestion |
| QA gate evaluation | Detect semantic errors | No — another stochastic call |
| Remediation loop | Fix detected errors | No — another stochastic call |

These are probabilistic. They improve the distribution of outputs but do not guarantee correctness. More governance on this layer does not converge — it just adds more rolls of the dice.

---

## Two Classes of Error

The MSA-001 findings reveal two fundamentally different error types that require different correction mechanisms:

### Structural Errors

Missing fields, wrong formats, schema violations, empty required arrays.

**Properties:**
- Mechanically detectable
- Mechanically preventable
- Fix once, fixed forever

**Example:** WS schema missing `verification_mode`, `preconditions`, `definition_of_done`. Fixed by adding them to the schema as required fields (v1.2.0). The system can never produce this error again.

**Correct response:** Convert to schema rule or mechanical validation.

### Semantic Errors

Contradictions across documents, scope overlap, missing prerequisites, inconsistent technology choices.

**Properties:**
- Require judgment to detect (often another LLM call)
- Cannot be mechanically prevented in the general case
- May recur because detection is itself stochastic

**Example:** TA says "hybrid AI" but WSs implement cloud-only. Detecting this requires understanding what "hybrid" means and checking whether the WSs cover local model execution. This is a judgment call, not a schema check.

**Current response:** Correction brief (prompt text) → hope LLM interprets correctly.

**Better response:** Structured correction with verifiable post-condition.

---

## The Gap: Corrections That Don't Change the Machine

ADR-069 (Rewind as Correction Gate) was a significant improvement. Before ADR-069, rewind was pure re-roll — no new information entered the system. After ADR-069, the operator can inject a correction brief that is dual-written to lineage (audit) and authority records (binding for regeneration).

But the correction brief is free text injected into the prompt via `{{operator_corrections}}`. The LLM may:

- Interpret it correctly
- Partially interpret it
- Ignore it
- Misinterpret it

There is no mechanical verification that the correction was applied. The system can make the same mistake twice because corrections don't change the machine — they whisper suggestions to it.

---

## Proposed Direction: Verifiable Post-Conditions

The gap is not in detection (the binder review, overlap evaluator, and contradiction detector all work). The gap is in what happens after detection.

A correction should have two parts:

1. **Text for the LLM:** Natural language describing what to do differently (what we have today).
2. **Verifiable assertion for the pipeline:** A machine-checkable post-condition that confirms the correction was applied.

Examples:

| Correction Intent | LLM Text | Verifiable Post-Condition |
|-------------------|----------|--------------------------|
| Remove Core ML from scope | "This is a cloud-first MVP. Do not include local/on-device AI components." | `excluded_terms: ["Core ML", "on-device", "local model"]` — reject output containing these terms |
| Merge duplicate WSs | "WS-069 and WS-075 cover the same scope. Produce a single merged WS." | `max_ws_count_for_scope("image storage"): 1` — reject if two WSs claim this scope |
| Fix technology inconsistency | "Use SFSpeechRecognizer, not Siri, for voice input." | `required_terms: ["SFSpeechRecognizer"]`, `excluded_terms: ["Siri"]` in voice-related WSs |
| Add missing prerequisite | "WS-081 requires a search controller. Add a WS that creates it." | `prerequisite_check: ws_exists_with_scope("search controller")` |

The LLM is still stochastic. But now the pipeline verifies the output against explicit post-conditions before accepting it. If verification fails, the specific failing component is regenerated — not the whole pipeline.

This is not implemented today. It represents a design direction, not a committed change.

---

## What This Does Not Change

This review does not invalidate the existing architecture. The following remain correct and valuable:

- **ADR-040 (Stateless Execution):** LLM invocations must remain stateless. The lesson is not "add memory" — it is "make the structured context carry more constraint."
- **ADR-049 (No Black Boxes):** Explicit composition is still required. The lesson is that composition should include post-condition verification, not just generation and evaluation.
- **ADR-064 (Durable Authority):** Authority records are the right accumulation mechanism. The lesson is that they should carry structured constraints, not just natural language.
- **POL-WS-001:** Work Statements still need explicit structure. The schema fix (v1.2.0) proves that mechanical enforcement works.
- **Governance, lineage, audit logging:** All remain essential. They are the selection and accumulation layer that does work.

---

## What This Changes

### Mental Model

| Before | After |
|--------|-------|
| Governance makes LLM output converge | Governance filters and constrains LLM output |
| Quality gates catch edge-case defects | Quality gates filter a stochastic process |
| Correction briefs steer generation | Correction briefs must produce verifiable post-conditions |
| The binder is the truth | The binder is the current best hypothesis, subject to iteration |
| Iteration is a governance problem to contain | Iteration is the mechanism of discovery; governance preserves what each pass teaches |

### Design Priorities

1. **Invest in mechanical validation over prompt engineering.** A schema rule that prevents an error forever is worth more than a prompt refinement that reduces its probability.
2. **Classify errors by type.** Structural errors get schema rules. Semantic errors get verifiable post-conditions. Do not treat all errors as prompt-tuning problems.
3. **Make corrections structural.** When an operator corrects a semantic error, the correction should produce both LLM text and a machine-checkable assertion.
4. **Accept stochasticity honestly.** The LLM is a probabilistic generator. Multiple independent checks (QA gate, overlap evaluator, contradiction detector, schema validation) compound reliability through redundancy, not determinism. This is valid — redundancy is an industrial principle that applies correctly here.
5. **Measure the right thing.** Success is not "the LLM produced the right output." Success is "the system did not allow wrong output to pass."

---

## Relationship to Agile/Iterative Development

This review also surfaces a tension with the pipeline's iteration model.

The Combine's pipeline was biased toward front-loading clarity: tighten intent through PGC, generate once, validate, ship. This is structurally similar to waterfall — not because it lacks quality checks, but because it assumes sufficient upstream rigor can replace iterative discovery.

It cannot. Intent is partially unknowable upfront. Some knowledge is only available after seeing an artifact, trying an approach, or noticing where reality resists assumptions. This is not sloppiness — it is how design works.

However, the current iteration mechanism (rewind + regenerate) is not true iteration. It is re-invocation of a stateless function with slightly different inputs. The LLM does not learn from failure. The system does not accumulate understanding. Each cycle is independent.

True iteration in the pipeline would require:
- Each pass produces a concrete artifact
- Review surfaces specific, actionable problems
- Problems become structured constraints (not just prompt text)
- Constraints are mechanically enforced on the next pass
- The constraint set grows monotonically — the system cannot regress

This is "governed iteration" as distinct from both waterfall (no iteration) and unstructured Agile (iteration without accumulation).

---

## Open Questions

1. **What is the right correction type system?** How many distinct post-condition types are needed? (Term exclusion, term requirement, count constraints, prerequisite existence checks, scope non-overlap assertions — what else?)

2. **Where do post-conditions live?** Authority records are the natural home, but they currently store natural language. Adding structured assertions requires schema changes to the authority record model.

3. **How do semantic post-conditions compose?** If two corrections both constrain the same document, do they AND together? Can they conflict?

4. **What is the cost/benefit of partial regeneration?** Regenerating one WS instead of the whole pipeline is cheaper, but may introduce incoherence with sibling documents that were generated together.

5. **Is stochastic detection of semantic errors good enough?** The QA gate, overlap evaluator, and contradiction detector are all LLM-based. Multiple independent stochastic checks compound reliability, but the system's overall error rate is bounded by the weakest detector. Is redundancy sufficient, or do some semantic checks need to become mechanical?

---

## The Convergence Illusion

A subtle failure mode was identified during the MSA-001 review cycle: **alignment of outputs mimics learning.**

When the operator rewinds and regenerates, the new output sometimes looks better. The natural conclusion is "we're converging." But nothing in the system changed. The LLM is stateless (ADR-040). The prompt is the same or slightly modified. The improvement is a different sample from the same distribution — not evidence of learning.

This is dangerous because:

- Later outputs look better than earlier ones, creating a sense of progress
- The operator's corrections feel impactful, reinforcing trust in the loop
- Plausible-looking output suppresses the skepticism that would otherwise catch errors

**The clean test:** After a correction, can the system still produce the same bad output? If yes, nothing was learned. If the failure mode has been mechanically eliminated (as with the schema v1.2.0 fix), learning occurred. If it was only addressed via prompt text, it was a suggestion, not a constraint.

---

## The Three-Layer Model

The original architecture implicitly placed intelligence in the pipeline — the expectation that LLM generation, given enough structure, would produce correct output. This is where the hypothesis broke.

The revised model separates three layers, each doing what it is actually good at:

| Layer | Role | Nature |
|-------|------|--------|
| **Pipeline** | Drafting | Stochastic. Produces raw material for review. Does not need to be smart — needs to produce something the Chorus can react to. |
| **Chorus** | Intelligence | Human + multiple AIs (Claude, GPT, others) reviewing, judging, correcting, deciding. This is where understanding lives. The Chorus is the system's intelligence — not the pipeline's LLM calls. |
| **Governance** | Memory and enforcement | Deterministic. Schemas, constraints, authority records, lineage. Preserves what the Chorus decided. Does not need judgment — the Chorus provides that. |

**The mistake was trying to put intelligence in the pipeline.** The pipeline is a drafting tool. It produces something for the Chorus to react to. That's all it needs to do.

The Chorus doesn't need to remember everything — the governance layer remembers for it. The governance layer doesn't need judgment — the Chorus provides that. Each layer does what it's good at.

**How this played out on 2026-04-03:** The pipeline produced MSA-001's binder. The Chorus (operator + GPT + Claude) reviewed it, found five findings, diagnosed the root cause (schema gap + semantic errors), and decided what to fix. The governance layer (schema v1.2.0, authority records, correction gate) encodes those decisions so they persist. The pipeline never got smarter. The Chorus did the thinking. The governance layer made it stick.

---

## Revised Scope: Personal AI Factory

The viability analysis (see conditions list below) reveals that The Combine's economics change fundamentally based on who the operator is.

**As a general-purpose product**, the system faces hard unsolved problems: operator qualification (condition 4), market fit (conditions 16-17), false confidence risk (condition 19), and the requirement that generated output be executable without significant rework (condition 18).

**As a personal system** — where the operator is the domain expert, the Chorus includes the operator + multiple AI collaborators, and the output serves the operator's own projects — most of the hard problems resolve:

| Condition | As Product | As Personal System |
|-----------|-----------|-------------------|
| Operator qualified to judge output | Must be assumed; risky | True by definition — operator is the expert |
| Market/product fit | Unvalidated | Irrelevant — operator is the customer |
| False confidence risk | High — polished output suppresses skepticism | Low — operator just spent months proving they don't trust the output |
| Cost tolerance | Must justify to customer | Personal decision |
| Generation quality bar | Must exceed "hire an architect" | Must exceed "me working alone" |

**The revised scope:** The Combine is a personal AI factory where the Chorus (operator + AI collaborators) is the intelligence, the pipeline is a drafting tool, and the governance layer is the memory. The operator reviews, corrects, and decides. The system remembers corrections and enforces them on regeneration. The output serves the operator's own projects.

**The long view:** As AI reasoning improves and partial determinism emerges, the boundary between Chorus and pipeline may shift — more judgment moves into the pipeline, less operator intervention required. The architecture supports this migration: the governance layer doesn't care whether a constraint came from a human correction or a mechanical rule. But this shift is not required for the system to be useful today.

---

## Viability Conditions

Twenty conditions that must be true for the system to be worth operating. Scored against current state.

### Generation Economics

1. **Correcting a generated draft must be faster than writing from scratch.** If it isn't, the system is negative value. *Status: Likely true for structural output; unvalidated for semantic quality.*

2. **The first draft must be structurally valid almost every time.** Schema compliance, required fields, correct format. *Status: True after v1.2.0 fix for WS documents. Other document types need audit.*

3. **Semantic errors must be visible, not hidden.** A wrong answer the operator catches is fine. A plausible-sounding wrong answer the operator accepts is catastrophic. *Status: Partially true — binder review surfaced errors, but the convergence illusion works against this.*

### Operator Model

4. **The operator must be qualified to judge the output.** *Status: True in personal-system scope — operator is the domain expert.*

5. **The correction loop must converge.** Each round must make output measurably better, not just different. *Status: Unknown — no measurement exists.*

6. **Total operator time must be less than manual equivalent.** *Status: Unmeasured.*

### Constraint Accumulation

7. **Corrections must become mechanical constraints, not just prompt suggestions.** *Status: Not true — corrections are prompt-level text (ADR-069). Verifiable post-conditions not yet implemented.*

8. **Upstream corrections must cascade downstream reliably.** *Status: Partially true — pipeline regenerates downstream stages, but correction propagation is via prompt injection, not mechanical.*

9. **The constraint set must grow monotonically.** *Status: True for schema rules (v1.2.0 fix persists). Not true for semantic corrections (prompt text, may be ignored).*

### Cost Model

10. **LLM cost per project must be bounded.** *Status: No circuit breaker on rewind cycles.*

11. **Infrastructure cost must be justified by throughput.** *Status: Resolved in personal-system scope.*

12. **Marginal cost of next project must be lower than the first.** *Status: True for schema/governance improvements. Unknown for semantic quality.*

### Pipeline Mechanics

13. **Generation must be fast enough that iteration isn't painful.** *Status: Acceptable — full pipeline runs in minutes.*

14. **Partial regeneration must be possible.** *Status: Not implemented — rewind regenerates from the target stage forward.*

15. **Validation must be mostly mechanical.** *Status: Mixed — schema validation is mechanical, QA gate is stochastic.*

### Product/Market (deprioritized in personal scope)

16. **Someone must value governed planning documents enough to pay.** *Status: N/A in personal scope.*

17. **The alternative must be worse.** *Status: Personal test — "faster than me alone."*

18. **The output must be executable.** *Status: Not yet validated — MSA-001 binder had execution-blocking findings.*

### Intellectual Honesty

19. **The system must not create false confidence.** *Status: Active risk — convergence illusion identified in this review.*

20. **The system must know when it's failing.** *Status: No success/failure metrics exist per project.*

---

## Conclusion

The Combine's industrial metaphor is valid but was applied at the wrong layer. Manufacturing principles do not make the machine tool (LLM) deterministic — they make the production line (pipeline) reliable despite the tool's variability. The system's strength is in selection, constraint, and accumulation. Its weakness is in treating generation quality as a governance problem solvable through prompt engineering and retry.

The revised architecture places intelligence in the Chorus (operator + AI collaborators), not in the pipeline. The pipeline drafts. The Chorus judges. The governance layer remembers. Each layer does what it is good at.

The immediate fix (WS schema v1.2.0) demonstrates the correct pattern: convert a class of errors into a mechanical rule that prevents recurrence. The longer-term direction is to extend this pattern to semantic errors through verifiable post-conditions on corrections.

The revised scope — a personal AI factory — resolves the hardest viability conditions (operator qualification, market fit, false confidence) and creates a controlled environment for validating the remaining conditions (correction convergence, constraint accumulation, cost bounds) against real projects.

The core hypothesis — that AI-driven knowledge work can be made reliable through industrial principles — survives, but with two critical refinements:

1. **Reliability comes from controlling what is accepted, not from controlling what is generated.**
2. **Intelligence lives in the Chorus, not in the pipeline. The pipeline is a drafting tool. The governance layer is the memory.**

As AI matures and reasoning becomes more reliable, the boundary between Chorus and pipeline may shift. The architecture supports this migration. But it is not required for the system to be useful today.

---

*This document is a living architectural review. It captures design insights and revised scope, not a committed implementation plan. Implementation of verifiable post-conditions would require a separate ADR and Work Statement process.*
