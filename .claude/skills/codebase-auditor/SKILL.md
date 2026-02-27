---
name: codebase-auditor
description: Audit the codebase for dead code, orphan config, broken references, dependency issues, and test coverage gaps. Use when asked to audit, find dead code, find orphans, check dependencies, find unused code, clean up, or produce a codebase health report. Also use before large cleanup work statements.
---

# Codebase Auditor

Produces structured audit reports for The Combine codebase. Finds what's dead, what's broken, what's orphaned, and what's missing.

## When to Use

- User says "audit the codebase", "find dead code", "what's orphaned"
- User says "find unused", "what's stale", "dependency check"
- Before writing cleanup Work Statements (provides the inventory)
- After major refactors (validates nothing was left behind)
- Periodically as a health check

## Output Location

All audit reports go to `docs/audits/` with timestamps:

```
docs/audits/YYYY-MM-DD-audit-summary.md       # Executive summary
docs/audits/YYYY-MM-DD-dead-code.md            # Dead code findings
docs/audits/YYYY-MM-DD-orphan-config.md        # Orphaned configuration
docs/audits/YYYY-MM-DD-dependency-graph.md     # Dependency analysis
docs/audits/YYYY-MM-DD-test-coverage-gaps.md   # Test coverage gaps
```

## Audit Modules

Run all modules by default. User can request specific modules.

---

### Module 1: Dead Code Detection (Python)

**Tools:** vulture, ruff, grep

**Procedure:**

1. Install vulture if not present:
   ```bash
   pip install vulture --break-system-packages
   ```

2. Run vulture on app code:
   ```bash
   vulture app/ --min-confidence 80
   ```

3. Run ruff for unused imports:
   ```bash
   ruff check app/ --select F401,F841 --output-format json
   ```
   - F401 = unused imports
   - F841 = unused local variables

4. Find Python files with zero importers (orphan modules):
   ```bash
   # For each .py file in app/, check if any other file imports it
   for f in $(find app/ -name "*.py" -not -name "__init__.py"); do
       module=$(echo "$f" | sed 's|/|.|g' | sed 's|\.py$||')
       short=$(basename "$f" .py)
       count=$(grep -rl "import.*$short\|from.*${module%.*}" app/ --include="*.py" | wc -l)
       if [ "$count" -le 1 ]; then
           echo "ORPHAN: $f (imported by $count files)"
       fi
   done
   ```

5. Find handler files not registered:
   ```bash
   # List all handler files
   ls app/domain/handlers/*.py | grep -v __init__ | grep -v registry | grep -v base
   # Cross-reference with registry.py imports
   grep "from.*handlers.*import" app/domain/handlers/registry.py
   ```

**Report format:**

```markdown
## Dead Code Report

### Unused Functions/Classes (vulture)
| File | Line | Name | Confidence |
|------|------|------|-----------|

### Unused Imports (ruff F401)
| File | Line | Import |
|------|------|--------|

### Orphan Modules (zero importers)
| File | Imported By |
|------|-------------|

### Unregistered Handlers
| Handler File | In Registry |
|-------------|-------------|
```

---

### Module 2: Orphan Configuration

**Scope:** combine-config/ ↔ app/ cross-reference

**Procedure:**

1. Parse active_releases.json:
   ```bash
   cat combine-config/_active/active_releases.json | python3 -c "
   import json, sys
   data = json.load(sys.stdin)
   for section, entries in data.items():
       if isinstance(entries, dict):
           for key, version in entries.items():
               print(f'{section}\t{key}\t{version}')
   "
   ```

2. For each document_type entry, verify:
   - Directory exists: `combine-config/document_types/{name}/releases/{version}/`
   - Package.yaml exists in that directory
   - Handler exists in app/domain/handlers/ (either `{name}_handler.py` or registered in registry.py)
   - At least one test file references it

3. For each workflow entry, verify:
   - Directory exists: `combine-config/workflows/{name}/releases/{version}/`
   - Definition file exists (definition.json or definition.yaml)
   - Referenced in software_product_development POW or has its own execution path

4. For each task entry, verify:
   - Prompt directory exists: `combine-config/prompts/tasks/{name}/releases/{version}/`
   - Task prompt file exists
   - Referenced by at least one document_type or workflow

5. For each schema entry, verify:
   - Schema directory exists: `combine-config/schemas/{name}/releases/{version}/`
   - Schema file exists
   - Referenced by at least one document_type package.yaml

6. Reverse check — find config directories NOT in active_releases:
   ```bash
   # List all doc type directories
   ls combine-config/document_types/
   # Compare against active_releases entries
   ```

**Report format:**

```markdown
## Orphan Configuration Report

### active_releases entries with missing directories
| Section | Key | Expected Path | Exists |
|---------|-----|---------------|--------|

### active_releases entries with no runtime consumer
| Section | Key | Handler | Tests | Verdict |
|---------|-----|---------|-------|---------|

### Config directories NOT in active_releases
| Path | Type | Status |
|------|------|--------|

### Document types without handlers
| Doc Type | Expected Handler | Registered |
|----------|-----------------|------------|

### Task prompts with no referencing document type
| Task | Referenced By |
|------|--------------|
```

---

### Module 3: JavaScript/SPA Dependency Analysis

**Tools:** grep, find (madge optional if installed)

**Procedure:**

1. Find orphan React components (never imported):
   ```bash
   for f in $(find spa/src/components -name "*.jsx" -o -name "*.tsx"); do
       name=$(basename "$f" | sed 's/\.\(jsx\|tsx\)$//')
       count=$(grep -rl "import.*$name\|from.*$name" spa/src/ --include="*.jsx" --include="*.tsx" --include="*.js" | grep -v "$f" | wc -l)
       if [ "$count" -eq 0 ]; then
           echo "ORPHAN: $f"
       fi
   done
   ```

2. Find unused JS utilities:
   ```bash
   for f in $(find spa/src/utils -name "*.js"); do
       name=$(basename "$f" .js)
       count=$(grep -rl "from.*utils.*$name\|import.*$name" spa/src/ --include="*.jsx" --include="*.tsx" --include="*.js" | grep -v "$f" | wc -l)
       if [ "$count" -eq 0 ]; then
           echo "UNUSED UTIL: $f"
       fi
   done
   ```

3. Find circular imports (basic detection):
   ```bash
   # Check if madge is available
   if command -v madge &>/dev/null; then
       madge --circular spa/src/
   else
       echo "madge not installed - skipping circular dependency check"
       echo "Install: npm install -g madge"
   fi
   ```

4. Check for stale SPA build artifacts:
   ```bash
   # Compare spa/src/ modification time against spa build output
   src_latest=$(find spa/src/ -name "*.jsx" -o -name "*.js" -o -name "*.css" | xargs stat -c %Y 2>/dev/null | sort -rn | head -1)
   build_latest=$(find app/web/static/spa/assets/ -type f | xargs stat -c %Y 2>/dev/null | sort -rn | head -1)
   if [ "$src_latest" -gt "$build_latest" ] 2>/dev/null; then
       echo "WARNING: SPA source is newer than build artifacts — rebuild needed"
   fi
   ```

**Report format:**

```markdown
## SPA Dependency Report

### Orphan Components (never imported)
| File | Exported Component |
|------|--------------------|

### Unused Utilities
| File |
|------|

### Circular Dependencies
| Cycle |
|-------|

### Build Staleness
| Status | Source Latest | Build Latest |
|--------|-------------|-------------|
```

---

### Module 4: Test Coverage Gaps

**Procedure:**

1. Find source files without corresponding test files:
   ```bash
   for f in $(find app/ -name "*.py" -not -name "__init__.py" -not -path "*/migrations/*"); do
       basename=$(basename "$f" .py)
       test_count=$(find tests/ -name "test_*${basename}*" -o -name "*${basename}*test*" 2>/dev/null | wc -l)
       if [ "$test_count" -eq 0 ]; then
           echo "UNTESTED: $f"
       fi
   done
   ```

2. Find test files without corresponding source files:
   ```bash
   for f in $(find tests/ -name "test_*.py"); do
       # Extract the subject from test filename
       subject=$(basename "$f" .py | sed 's/^test_//')
       source_count=$(find app/ -name "*${subject}*" 2>/dev/null | wc -l)
       if [ "$source_count" -eq 0 ]; then
           echo "ORPHAN TEST: $f (no matching source)"
       fi
   done
   ```

3. Find test files that import deleted/renamed modules:
   ```bash
   # Run a quick import check
   for f in $(find tests/ -name "*.py"); do
       python3 -c "import ast; ast.parse(open('$f').read())" 2>/dev/null
       if [ $? -ne 0 ]; then
           echo "SYNTAX ERROR: $f"
       fi
   done
   ```

4. Count tests per tier:
   ```bash
   echo "Tier 1: $(find tests/tier1/ -name "test_*.py" -exec grep -l "def test_" {} \; | wc -l) files"
   echo "Tier 2: $(find tests/tier2/ -name "test_*.py" -exec grep -l "def test_" {} \; 2>/dev/null | wc -l) files"
   echo "Integration: $(find tests/integration/ -name "test_*.py" -exec grep -l "def test_" {} \; 2>/dev/null | wc -l) files"
   echo "Unit: $(find tests/unit/ -name "test_*.py" -exec grep -l "def test_" {} \; 2>/dev/null | wc -l) files"
   ```

**Report format:**

```markdown
## Test Coverage Gaps

### Source files without tests
| Source File | Expected Test |
|------------|---------------|

### Orphan test files (no matching source)
| Test File | Expected Source |
|-----------|----------------|

### Tests with import errors
| Test File | Error |
|-----------|-------|

### Test Distribution
| Tier | File Count | Test Count |
|------|-----------|------------|
```

---

### Module 5: Cross-Cutting Reference Audit

**Purpose:** Find specific term contamination across the codebase.

**Default search terms:** `epic`, `feature`, `backlog_item`, `story_backlog`, `primary_implementation_plan`

**User can provide additional terms.**

**Procedure:**

```bash
for term in epic feature backlog_item story_backlog primary_implementation_plan; do
    echo "=== $term ==="
    echo "-- combine-config/ --"
    grep -rl "$term" combine-config/ --include="*.json" --include="*.yaml" --include="*.txt" 2>/dev/null | wc -l
    echo "-- app/ --"
    grep -rl "$term" app/ --include="*.py" --include="*.html" --include="*.js" --include="*.jsx" 2>/dev/null | wc -l
    echo "-- tests/ --"
    grep -rl "$term" tests/ --include="*.py" 2>/dev/null | wc -l
    echo "-- spa/src/ --"
    grep -rl "$term" spa/src/ --include="*.jsx" --include="*.js" 2>/dev/null | wc -l
    echo ""
done
```

**Report format:**

```markdown
## Cross-Cutting Reference Audit

### Term: `epic`
| Area | File Count | Files |
|------|-----------|-------|

### Term: `primary_implementation_plan`
| Area | File Count | Files |
|------|-----------|-------|

(etc.)
```

---

## Executive Summary Template

After running all modules, produce a summary:

```markdown
# Codebase Audit Summary — YYYY-MM-DD

## Health Score

| Metric | Count | Severity |
|--------|-------|----------|
| Dead code (functions/classes) | N | |
| Unused imports | N | |
| Orphan Python modules | N | |
| Orphan config entries | N | |
| Config without runtime consumer | N | |
| Orphan React components | N | |
| Source files without tests | N | |
| Orphan test files | N | |
| Contamination terms found | N | |

## Critical (Act Now)
- Items that will cause runtime failures or test failures

## High (Act Soon)
- Dead code that adds confusion or maintenance burden
- Orphan config that inflates deployment or wastes tokens

## Medium (Track as Debt)
- Test coverage gaps
- Stale build artifacts

## Low (Informational)
- Style issues, naming inconsistencies

## Recommended Work Statements
Based on findings, the following WSs are recommended:
- WS-XXX: [description based on critical findings]
- WS-XXX: [description based on high findings]
```

---

## Rules

1. **Never modify code during an audit.** Audits are read-only. Produce reports, not fixes.
2. **Report facts, not opinions.** "File X has zero importers" not "File X seems unnecessary."
3. **Include file paths and line numbers** so findings are actionable.
4. **Cross-reference, don't guess.** If unsure whether something is dead, mark it as "VERIFY" not "DEAD."
5. **Run from repo root.** All paths are relative to `/home/tommoseley/dev/TheCombine/`.
6. **Respect the recycle/ convention.** Files in `recycle/` are already marked for deletion — don't re-report them.
7. **Exclude docs/ and docs/archive/.** Documentation is append-only, not subject to dead code analysis.
8. **Exclude alembic/versions/.** Migrations are historical and must not be flagged as dead.

## Quick Commands

```bash
# Full audit
# (Run each module's commands in sequence, collect output into report files)

# Quick contamination check for a specific term
grep -rn "YOUR_TERM" app/ tests/ combine-config/ spa/src/ --include="*.py" --include="*.json" --include="*.yaml" --include="*.jsx" --include="*.js"

# Quick orphan handler check
diff <(ls app/domain/handlers/*_handler.py | xargs -I{} basename {} _handler.py | sort) \
     <(grep "from.*handlers.*import" app/domain/handlers/registry.py | grep -oP '\w+(?=Handler)' | tr '[:upper:]' '[:lower:]' | sort)

# Quick active_releases vs directory check
python3 -c "
import json
with open('combine-config/_active/active_releases.json') as f:
    data = json.load(f)
for key in data.get('document_types', {}):
    import os
    path = f'combine-config/document_types/{key}'
    exists = os.path.isdir(path)
    if not exists:
        print(f'MISSING DIR: {path}')
"
```