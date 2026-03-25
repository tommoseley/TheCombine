# PROC-PROMPT-TUNING-001: Prompt Tuning Process

| | |
|---|---|
| **Status** | Active |
| **Effective Date** | 2026-03-18 |
| **Applies To** | All prompt versions for governed artifact types |
| **Related Artifacts** | ADR-058, WS-PI-3A through WS-PI-3C, wp_defect_evaluator, ws_defect_evaluator |

---

## 1. Purpose

Controlled prompt improvement triggered by quality signals. One defect per cycle, measured before and after, no guessing.

---

## 2. Trigger Conditions

### Primary Triggers

| ID | Trigger | Example |
|----|---------|---------|
| T1 | Defect threshold breach | Any evaluator rule >10% fail rate, or new defect class appears |
| T2 | New capability introduction | New prompt version, new artifact type, or new evaluator rule added |
| T3 | Dataset expansion | New scenarios added to baseline, production runs added to replay pool |

### Secondary Triggers

| ID | Trigger | Example |
|----|---------|---------|
| T4 | Drift detection | Previously stable metric degrades over time |
| T5 | Manual invocation | Explicit decision to improve a known weakness |

---

## 3. Process Steps

```
Trigger → Baseline → Select Defect → Tune → Replay → Verify → Promote → Monitor
```

### Step 0 — Gate Check

Before starting, confirm:
- Replay harness operational
- Evaluator stable
- Dataset defined

If not, abort.

### Step 1 — Baseline Run

Execute dataset through system. Capture defect distribution and pass/fail rates.

**Output:** Baseline Snapshot

### Step 2 — Defect Selection

Select **one defect class only**. Selection rules:
- Highest frequency, OR
- Highest impact

**Output:** Target Defect

### Step 3 — Tuning Plan

Create a minimal WS defining:
- Target field
- Expected behavior change
- Acceptance criteria

### Step 4 — Prompt Modification

Implement minimal prompt change. Version increment (e.g., v1.1.1 → v1.1.2).

Constraints:
- No unrelated changes
- No verbosity inflation

### Step 5 — Replay

Run same dataset. No other system changes.

### Step 6 — Verification

Compare baseline vs new. Must confirm:
- Target defect reduced or eliminated
- No regressions
- No new critical defects

### Step 7 — Promotion Decision

| Result | Action |
|--------|--------|
| PASS | Activate prompt in runtime, record version + change |
| FAIL | Revert or iterate (same defect only) |

### Step 8 — Monitoring

After promotion, observe production runs. Watch for drift and new defect classes.

---

## 4. Constraints

- One defect per cycle
- Fixed dataset during cycle
- Evaluator unchanged during cycle
- Deterministic checks only

---

## 5. Outputs Per Cycle

- Baseline Snapshot
- Defect Selection
- Tuning WS
- Delta Report
- Prompt Version Update

---

## 6. When NOT to Run

Do not run when:
- No measurable defects exist
- Dataset is saturated with no new signal
- System changes would confound results

In those cases: expand dataset or shift to another artifact layer.

---

## 7. Validation Evidence

First application (2026-03-18):

| Metric | v1.1.0 (baseline) | v1.1.1 (tuned) |
|--------|-------------------|----------------|
| semantic_scope fail rate | 20% | 0% |
| Total defects | 1 | 0 |
| Regressions | — | 0 |

Defect: WP-AMBIGUOUS-004 `scope_in: ["UI improvements"]` → 4 concrete investigation activities.
