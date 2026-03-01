---
name: crap-refactor
description: Analyze codebase testability using CRAP scores (Change Risk Anti-Patterns), rank functions by risk, and generate bounded refactoring Work Statements. Use when asked to improve testability, reduce complexity, find untestable code, compute CRAP scores, refactor for coverage, or improve separation of concerns. Phase 1 is read-only analysis. Phase 2 executes accepted Work Statements.
---

# CRAP Score Refactoring

Computes CRAP (Change Risk Anti-Patterns) scores across the codebase, ranks functions by testability risk, and produces bounded Work Statements for refactoring in human-approved batches.

## Formula

```
CRAP(f) = complexity(f)^2 * (1 - coverage(f)/100)^3 + complexity(f)
```

Where:
- `complexity(f)` = cyclomatic complexity of function f
- `coverage(f)` = line coverage percentage of function f (0-100)

**Interpretation:**
- CRAP < 5: Clean — low complexity, well tested
- CRAP 5-15: Acceptable — moderate risk
- CRAP 15-30: Smelly — refactor when touched
- CRAP > 30: Critical — high change risk, refactor proactively

A function with complexity 10 and 0% coverage has CRAP = 110.
A function with complexity 10 and 95% coverage has CRAP = 10.0125.
Complexity alone doesn't condemn a function — untested complexity does.

## When to Use

- User says "compute CRAP scores", "find untestable code", "testability audit"
- User says "improve coverage", "refactor for testability", "separation of concerns"
- User says "what's the riskiest code", "what should we test next"
- After a codebase audit reveals low test coverage areas
- Before major feature work in a subsystem (reduce risk first)

## Prerequisites

Install tooling if not present:
```bash
pip install pytest-cov radon --break-system-packages
```

Verify:
```bash
radon cc --version
python -m pytest --co -q 2>&1 | head -3
```

## Phase 1: Analysis (Read-Only)

Phase 1 is always safe to run. No code changes. Produces reports and draft Work Statements.

### Step 1: Collect Cyclomatic Complexity

```bash
# JSON output: complexity per function/method/class
radon cc app/ -j -n C > /tmp/combine_complexity.json
```

The `-n C` flag filters to complexity grade C or worse (complexity >= 11). To see everything:

```bash
radon cc app/ -j > /tmp/combine_complexity_all.json
```

Parse the JSON. Each entry has:
- `name`: function/method name
- `classname`: containing class (if method)
- `lineno`: line number
- `complexity`: cyclomatic complexity score
- `filename`: source file

### Step 2: Collect Test Coverage

```bash
# Run tests with coverage, output JSON
python -m pytest tests/tier1/ tests/unit/ -x -q \
    --cov=app \
    --cov-report=json:/tmp/combine_coverage.json \
    --cov-report=term-missing \
    -m "not slow" \
    2>&1 | tail -20
```

**Important:** Only run Tier-1 and unit tests for coverage. Do NOT run integration or e2e tests — they inflate coverage numbers with incidental coverage that doesn't represent intentional testing.

The JSON output contains per-file line coverage. We need to map this to per-function coverage.

### Step 3: Compute Per-Function Coverage

For each function identified by radon, determine its line coverage:

```python
"""
Compute per-function coverage from pytest-cov JSON output + radon complexity.

Usage: python ops/scripts/crap_analysis.py
Output: docs/audits/YYYY-MM-DD-crap-scores.md
"""
import json
import ast
import sys
from pathlib import Path
from datetime import date

def get_function_lines(filepath, func_name, lineno):
    """Get the line range for a function using AST parsing."""
    try:
        source = Path(filepath).read_text()
        tree = ast.parse(source)
    except (SyntaxError, FileNotFoundError):
        return set()
    
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == func_name and node.lineno == lineno:
                # Get all line numbers in this function
                lines = set()
                for child in ast.walk(node):
                    if hasattr(child, 'lineno'):
                        lines.add(child.lineno)
                return lines
    return set()

def compute_function_coverage(filepath, func_lines, coverage_data):
    """Compute coverage percentage for a specific function."""
    file_cov = coverage_data.get("files", {}).get(filepath)
    if not file_cov or not func_lines:
        return 0.0
    
    executed = set(file_cov.get("executed_lines", []))
    missing = set(file_cov.get("missing_lines", []))
    
    func_executed = func_lines & executed
    func_missing = func_lines & missing
    func_total = func_executed | func_missing
    
    if not func_total:
        return 0.0
    
    return (len(func_executed) / len(func_total)) * 100

def crap_score(complexity, coverage_pct):
    """Compute CRAP score."""
    return (complexity ** 2) * ((1 - coverage_pct / 100) ** 3) + complexity

# Load data
with open("/tmp/combine_complexity.json") as f:
    complexity_data = json.load(f)

with open("/tmp/combine_coverage.json") as f:
    coverage_data = json.load(f)

# Compute scores
results = []
for filepath, functions in complexity_data.items():
    for func in functions:
        if func["type"] in ("function", "method"):
            func_lines = get_function_lines(
                filepath, func["name"], func["lineno"]
            )
            coverage = compute_function_coverage(
                filepath, func_lines, coverage_data
            )
            score = crap_score(func["complexity"], coverage)
            results.append({
                "file": filepath,
                "function": func["name"],
                "class": func.get("classname", ""),
                "line": func["lineno"],
                "complexity": func["complexity"],
                "coverage": round(coverage, 1),
                "crap": round(score, 1),
            })

# Sort by CRAP score descending
results.sort(key=lambda r: r["crap"], reverse=True)

# Output
for r in results[:50]:
    qual = (f"{r['class']}." if r['class'] else "") + r['function']
    print(f"CRAP={r['crap']:>8.1f}  CC={r['complexity']:>3}  "
          f"Cov={r['coverage']:>5.1f}%  {r['file']}:{r['line']}  {qual}")
```

Save this script as `ops/scripts/crap_analysis.py`. It can be reused across sessions.

### Step 4: Generate CRAP Report

Produce `docs/audits/YYYY-MM-DD-crap-scores.md`:

```markdown
# CRAP Score Analysis - YYYY-MM-DD

## Summary

| Metric | Count |
|--------|-------|
| Functions analyzed | N |
| CRAP > 30 (Critical) | N |
| CRAP 15-30 (Smelly) | N |
| CRAP 5-15 (Acceptable) | N |
| CRAP < 5 (Clean) | N |
| Median CRAP score | N |

## Critical Functions (CRAP > 30)

| CRAP | CC | Coverage | File | Function |
|------|-----|----------|------|----------|
| 110.0 | 10 | 0.0% | app/domain/handlers/foo.py:45 | process() |
| ... | | | | |

## Smelly Functions (CRAP 15-30)

| CRAP | CC | Coverage | File | Function |
|------|-----|----------|------|----------|
| ... | | | | |

## By Subsystem

### Document Generation (app/domain/handlers/, app/domain/services/)
| CRAP | CC | Coverage | File | Function |
|------|-----|----------|------|----------|

### Workflow Engine (app/domain/workflow/)
| CRAP | CC | Coverage | File | Function |
|------|-----|----------|------|----------|

### API Layer (app/api/)
| CRAP | CC | Coverage | File | Function |
|------|-----|----------|------|----------|

(etc. for each subsystem)
```

### Step 5: Generate Draft Work Statements

For each subsystem with Critical functions, generate a draft WS.

**Batching rules:**
- Maximum 5-10 functions per WS
- Group by subsystem (don't mix handlers with workflow engine)
- Prioritize by CRAP score (worst first within batch)
- Each WS must be independently executable and independently verifiable

**WS template:**

```markdown
# WS-CRAP-{NNN}: Testability Refactoring - {Subsystem} Batch {N}

## Status: Draft (generated by crap-refactor skill)

## Parent Work Package
WP-CRAP-001: Testability Refactoring

## Target Functions

| # | CRAP | CC | Coverage | File | Function | Proposed Action |
|---|------|-----|----------|------|----------|-----------------|
| 1 | 110.0 | 10 | 0.0% | app/domain/handlers/foo.py:45 | process() | Extract pure logic |
| 2 | 85.0 | 8 | 5.0% | app/domain/handlers/foo.py:120 | validate() | Split validation |
| ... | | | | | | |

## Refactoring Strategy

For each function:
1. Identify pure logic that can be extracted (no DB, no LLM, no I/O)
2. Extract into a standalone function or method in the same module or a new helper
3. Write Tier-1 tests for the extracted logic
4. Thin the original function to delegate to the extracted logic
5. Verify CRAP score dropped below threshold

## Acceptance Criteria

1. All target functions have CRAP score < 30 after refactoring
2. Test coverage for target functions is > 70%
3. No behavioral changes (existing tests still pass)
4. Tier-0 green
5. New tests are Tier-1 (in-memory, no DB, no I/O)

## Prohibited Actions

- Do NOT change function signatures that are part of the public API
- Do NOT merge or delete existing test files
- Do NOT refactor functions not listed in Target Functions
- Do NOT add database dependencies to extracted functions
- Do NOT run tests -- provide instructions only

## Post-Refactoring Verification

After completing all extractions:
1. Recompute CRAP scores for target functions
2. Produce before/after comparison table
3. Verify all existing tests pass
4. Verify new Tier-1 tests pass
```

**Output location:** `docs/work-statements/WS-CRAP-{NNN}.md`

Also generate the parent WP if it doesn't exist:

```markdown
# WP-CRAP-001: Testability Refactoring

## Status: Draft (generated by crap-refactor skill)

## Intent

Systematically reduce Change Risk Anti-Pattern (CRAP) scores across the
codebase by extracting testable logic from high-complexity, low-coverage
functions. Each WS targets a bounded batch of functions in one subsystem.

## Work Statements (generated)

| WS | Subsystem | Functions | Worst CRAP | Status |
|----|-----------|-----------|------------|--------|
| WS-CRAP-001 | Handlers | 8 | 110.0 | Draft |
| WS-CRAP-002 | Workflow | 5 | 85.0 | Draft |
| ... | | | | |

## Scope Out
- Architectural redesign (these are targeted extractions, not rewrites)
- New features or capabilities
- Database schema changes
- Prompt content changes
```

### Phase 1 Complete

At this point, stop and present findings to the user:
- CRAP report location
- Number of Critical/Smelly functions
- Draft WS count and locations
- Ask: "Review the draft WSs. Which would you like to accept for execution?"

**Do NOT proceed to Phase 2 without explicit user acceptance of specific WSs.**

---

## Phase 2: Refactoring (Requires Accepted WS)

Phase 2 executes an accepted Work Statement. Follow the WS steps exactly.

### Refactoring Patterns

When extracting logic from high-CRAP functions, use these patterns:

**Pattern A: Extract Pure Logic**
```python
# BEFORE (CRAP=110, CC=10, Cov=0%)
class FooHandler:
    async def process(self, doc, session):
        # 50 lines mixing DB queries, validation, transformation, LLM calls
        ...

# AFTER
# New: testable pure function
def transform_foo_inputs(raw_data: dict, config: dict) -> dict:
    """Pure transformation logic, no I/O."""
    # 30 lines of the original logic, extracted
    ...

# Thinned: handler delegates
class FooHandler:
    async def process(self, doc, session):
        raw = await self._fetch_inputs(doc, session)  # I/O
        transformed = transform_foo_inputs(raw, self.config)  # Pure
        await self._persist(transformed, session)  # I/O
```

**Pattern B: Split Conditional Complexity**
```python
# BEFORE (CC=15 from nested if/elif chains)
def route_document(doc):
    if doc.type == "a":
        if doc.state == "x":
            ...
        elif doc.state == "y":
            ...
    elif doc.type == "b":
        ...

# AFTER
ROUTING_TABLE = {
    ("a", "x"): route_a_x,
    ("a", "y"): route_a_y,
    ("b", None): route_b,
}

def route_document(doc):
    handler = ROUTING_TABLE.get((doc.type, doc.state))
    if handler:
        return handler(doc)
    raise UnknownRouteError(doc.type, doc.state)
```

**Pattern C: Extract Validation**
```python
# BEFORE (validation mixed with business logic)
def create_work_package(data, project, ta_doc):
    if not data.get("title"):
        raise ValueError("title required")
    if len(data["title"]) > 200:
        raise ValueError("title too long")
    if not ta_doc:
        raise ValueError("TA required")
    # ... 30 more lines of actual creation logic

# AFTER
def validate_work_package_inputs(data: dict, ta_doc) -> list[str]:
    """Pure validation, returns list of errors."""
    errors = []
    if not data.get("title"):
        errors.append("title required")
    if len(data.get("title", "")) > 200:
        errors.append("title too long")
    if not ta_doc:
        errors.append("TA required")
    return errors

def create_work_package(data, project, ta_doc):
    errors = validate_work_package_inputs(data, ta_doc)
    if errors:
        raise ValidationError(errors)
    # ... clean creation logic only
```

### Test Writing Rules

1. **Tier-1 only.** Extracted functions get in-memory tests. No database. No file I/O. No LLM.
2. **Test the extraction, not the wrapper.** The original function keeps its existing tests (if any). New tests target the extracted pure function.
3. **Edge cases matter.** High CC means many branches. Each branch needs at least one test.
4. **Use the existing test fixtures** from `tests/fixtures/` where applicable.
5. **Follow existing naming:** `tests/tier1/{subsystem}/test_{module}.py`

### Post-Batch Verification

After completing a WS batch:

1. Recompute CRAP scores for all target functions:
   ```bash
   # Re-run analysis
   radon cc {files_touched} -j > /tmp/crap_after.json
   python -m pytest tests/tier1/ -x -q --cov=app --cov-report=json:/tmp/cov_after.json -m "not slow"
   python ops/scripts/crap_analysis.py
   ```

2. Produce before/after table:
   ```markdown
   ## Before/After CRAP Scores

   | Function | Before | After | Delta |
   |----------|--------|-------|-------|
   | handler.process() | 110.0 | 12.5 | -97.5 |
   | handler.validate() | 85.0 | 8.2 | -76.8 |
   ```

3. Provide test run instructions to human.

---

## Rules

1. **Phase 1 is always read-only.** No code changes during analysis.
2. **Phase 2 requires an accepted WS.** Never refactor without explicit human acceptance.
3. **Batch size: 5-10 functions max per WS.** Larger batches are ungovernable.
4. **No behavioral changes.** Refactoring must preserve existing behavior. If existing tests break, the extraction was wrong.
5. **Extract, don't rewrite.** Move logic out, don't redesign it. Redesign is a separate WS with different governance.
6. **Run from repo root.** All paths relative to `/home/tommoseley/dev/TheCombine/`.
7. **Respect the testing rule.** Do NOT run tests. Provide instructions only.
8. **Score improvement is the metric.** If CRAP didn't drop, the refactoring didn't work.

## Quick Commands

```bash
# Full CRAP analysis (Phase 1)
radon cc app/ -j > /tmp/combine_complexity.json
python -m pytest tests/tier1/ tests/unit/ -x -q --cov=app --cov-report=json:/tmp/combine_coverage.json -m "not slow"
python ops/scripts/crap_analysis.py

# Quick complexity check on a single file
radon cc app/domain/handlers/some_handler.py -s

# Quick coverage for a single module
python -m pytest tests/tier1/ -x -q --cov=app.domain.handlers.some_handler --cov-report=term-missing -m "not slow"

# Complexity distribution (how many functions at each grade)
radon cc app/ -s -n A | grep -c "^    "  # Grade A count
radon cc app/ -s -n B | grep -c "^    "  # Grade B+ count
radon cc app/ -s -n C | grep -c "^    "  # Grade C+ count
```
