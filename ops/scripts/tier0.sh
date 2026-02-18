#!/usr/bin/env bash
# =============================================================================
# Tier 0 Verification Harness (WS-ADR-050-001, hardened per ADR-050)
#
# Mandatory baseline checks for all Combine work.
# Returns zero only when all checks pass. Missing tooling is a FAILURE
# unless explicitly declared as a Mode B exception via --allow-missing.
#
# Usage:
#   ops/scripts/tier0.sh                              # pytest + lint + typecheck
#   ops/scripts/tier0.sh --allow-missing typecheck     # Mode B: accept missing mypy
#   ops/scripts/tier0.sh --frontend                    # force SPA build
#   ops/scripts/tier0.sh --scope app/ tests/           # validate file scope
#
# Checks:
#   1. Backend tests  (pytest)
#   2. Backend lint   (ruff)   — changed/new files only
#   3. Backend types  (mypy)   — FAILS if missing, unless --allow-missing typecheck
#   4. Frontend build (vite)   — auto-runs when spa/ files changed, or --frontend
#   5. Scope validation        — only with --scope
#
# Mode B:
#   --allow-missing <check>  declares a Mode B exception for a missing tool.
#   Mode B checks are logged, emit B-MODE ACTIVE, and appear as SKIP_B in
#   the machine-readable summary. Mode B is debt, not a free pass.
#
# CI enforcement:
#   When CI=true, --allow-missing is rejected unless ALLOW_MODE_B_IN_CI=1.
#   This prevents shipping with Mode B debt by accident.
#
# Machine-readable output:
#   A single-line JSON object is always emitted after the --- TIER0_JSON ---
#   marker, even on failure. Schema version is included for forward compat.
# =============================================================================

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------
STARTED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
START_EPOCH_MS=$(date +%s%3N 2>/dev/null || echo $(($(date +%s) * 1000)))

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
FRONTEND_FORCED=false
SCOPE_PATHS=()
ALLOWED_MISSING=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --frontend)
            FRONTEND_FORCED=true
            shift
            ;;
        --scope)
            shift
            while [[ $# -gt 0 && ! "$1" =~ ^-- ]]; do
                SCOPE_PATHS+=("$1")
                shift
            done
            ;;
        --allow-missing)
            shift
            if [[ $# -eq 0 ]]; then
                echo "ERROR: --allow-missing requires a check name" >&2
                exit 2
            fi
            ALLOWED_MISSING+=("$1")
            shift
            ;;
        *)
            echo "ERROR: Unknown argument: $1" >&2
            echo "Usage: tier0.sh [--frontend] [--scope path1 ...] [--allow-missing check ...]" >&2
            exit 2
            ;;
    esac
done

# ---------------------------------------------------------------------------
# CI guard: reject --allow-missing in CI unless explicitly permitted
# ---------------------------------------------------------------------------
if [[ "${CI:-}" == "true" && ${#ALLOWED_MISSING[@]} -gt 0 ]]; then
    if [[ "${ALLOW_MODE_B_IN_CI:-}" != "1" ]]; then
        echo "FAIL: --allow-missing is not permitted in CI." >&2
        echo "Mode B exceptions in CI require ALLOW_MODE_B_IN_CI=1." >&2
        echo "Requested exceptions: ${ALLOWED_MISSING[*]}" >&2
        exit 1
    fi
    echo "WARNING: Mode B allowed in CI via ALLOW_MODE_B_IN_CI=1 (checks: ${ALLOWED_MISSING[*]})"
fi

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
is_allowed_missing() {
    local check="$1"
    for allowed in "${ALLOWED_MISSING[@]+"${ALLOWED_MISSING[@]}"}"; do
        if [[ "$allowed" == "$check" ]]; then
            return 0
        fi
    done
    return 1
}

# ---------------------------------------------------------------------------
# Collect changed files (used by lint, frontend detection, scope)
# ---------------------------------------------------------------------------
# In CI with a known base branch, diff against merge-base for accurate
# branch-level change detection. Locally, diff against HEAD for uncommitted.
if [[ "${CI:-}" == "true" ]]; then
    # GitHub Actions: GITHUB_BASE_REF for PRs, fall back to origin/main
    # Custom override: TIER0_DIFF_BASE
    if [[ -n "${TIER0_DIFF_BASE:-}" ]]; then
        DIFF_BASE="$TIER0_DIFF_BASE"
    elif [[ -n "${GITHUB_BASE_REF:-}" ]]; then
        DIFF_BASE=$(git merge-base "origin/${GITHUB_BASE_REF}" HEAD 2>/dev/null || echo HEAD)
    else
        DIFF_BASE=$(git merge-base origin/main HEAD 2>/dev/null || echo HEAD)
    fi
    echo "CI mode: diff base = ${DIFF_BASE}"
    changed_files=$(git diff --name-only "$DIFF_BASE"...HEAD 2>/dev/null || true)
    new_untracked=""
else
    # Local dev: uncommitted changes + untracked files
    changed_files=$(git diff --name-only HEAD 2>/dev/null || true)
    changed_staged=$(git diff --name-only --cached 2>/dev/null || true)
    changed_files=$(echo -e "${changed_files}\n${changed_staged}" || true)
    new_untracked=$(git ls-files --others --exclude-standard 2>/dev/null || true)
fi

ALL_CHANGED=$(echo -e "${changed_files}\n${new_untracked}" \
    | sort -u | grep -v '^$' || true)

# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------
declare -A RESULTS
MODE_B_CHECKS=()
OVERALL_EXIT=0

# ---------------------------------------------------------------------------
# Check 1: Backend tests (pytest)
# ---------------------------------------------------------------------------
echo "=== CHECK 1: Backend Tests (pytest) ==="
# Ignore harness meta-tests to avoid recursive invocation
python -m pytest tests/ -x -q \
    --ignore=tests/infrastructure/test_tier0_harness.py \
    2>&1
RESULTS[pytest]=$?

if [[ ${RESULTS[pytest]} -ne 0 ]]; then
    echo "FAIL: pytest"
    OVERALL_EXIT=1
else
    echo "PASS: pytest"
fi

# ---------------------------------------------------------------------------
# Check 2: Backend lint (ruff) — changed/new files only
# ---------------------------------------------------------------------------
echo ""
echo "=== CHECK 2: Backend Lint (ruff) ==="

if ! command -v ruff &>/dev/null; then
    if is_allowed_missing "lint"; then
        echo "B-MODE ACTIVE: lint (ruff not installed)"
        RESULTS[lint]="SKIP_B"
        MODE_B_CHECKS+=("lint")
    else
        echo "FAIL: ruff not installed. Use --allow-missing lint to declare Mode B."
        RESULTS[lint]=1
        OVERALL_EXIT=1
    fi
else
    # "No worse than baseline": lint only changed/new Python files.
    lint_targets=$(echo "$ALL_CHANGED" \
        | grep '\.py$' \
        | grep -E '^(app|tests)/' \
        | sort -u || true)

    if [[ -n "$lint_targets" ]]; then
        echo "$lint_targets" | xargs ruff check 2>&1
        RESULTS[lint]=$?
    else
        echo "No changed Python files to lint"
        RESULTS[lint]=0
    fi

    if [[ "${RESULTS[lint]}" != "SKIP_B" ]]; then
        if [[ ${RESULTS[lint]} -ne 0 ]]; then
            echo "FAIL: lint"
            OVERALL_EXIT=1
        else
            echo "PASS: lint"
        fi
    fi
fi

# ---------------------------------------------------------------------------
# Check 3: Backend type check (mypy)
# ---------------------------------------------------------------------------
echo ""
echo "=== CHECK 3: Backend Type Check (mypy) ==="

if ! command -v mypy &>/dev/null; then
    if is_allowed_missing "typecheck"; then
        echo "B-MODE ACTIVE: typecheck (mypy not installed)"
        RESULTS[typecheck]="SKIP_B"
        MODE_B_CHECKS+=("typecheck")
    else
        echo "FAIL: mypy not installed. Use --allow-missing typecheck to declare Mode B."
        RESULTS[typecheck]=1
        OVERALL_EXIT=1
    fi
else
    mypy app/ 2>&1
    RESULTS[typecheck]=$?
    if [[ ${RESULTS[typecheck]} -ne 0 ]]; then
        echo "FAIL: typecheck"
        OVERALL_EXIT=1
    else
        echo "PASS: typecheck"
    fi
fi

# ---------------------------------------------------------------------------
# Check 4: Frontend build (auto-detect or --frontend)
# ---------------------------------------------------------------------------
echo ""
echo "=== CHECK 4: Frontend Build ==="

# Auto-detect: any changed/new files under spa/?
spa_changed=$(echo "$ALL_CHANGED" | grep -E '^spa/' || true)
RUN_FRONTEND=false

if [[ "$FRONTEND_FORCED" == "true" ]]; then
    RUN_FRONTEND=true
    echo "(forced via --frontend)"
elif [[ -n "$spa_changed" ]]; then
    RUN_FRONTEND=true
    echo "(auto-detected spa/ changes)"
fi

if [[ "$RUN_FRONTEND" == "true" ]]; then
    if [[ -d "$REPO_ROOT/spa" ]]; then
        (cd "$REPO_ROOT/spa" && npm run build) 2>&1
        RESULTS[frontend]=$?
        if [[ ${RESULTS[frontend]} -ne 0 ]]; then
            echo "FAIL: frontend"
            OVERALL_EXIT=1
        else
            echo "PASS: frontend"
        fi
    else
        echo "WARNING: spa/ directory not found"
        RESULTS[frontend]=1
        OVERALL_EXIT=1
    fi
else
    echo "SKIPPED (no spa/ changes detected; use --frontend to force)"
    RESULTS[frontend]="SKIP"
fi

# ---------------------------------------------------------------------------
# Check 5: Scope validation (conditional)
# ---------------------------------------------------------------------------
echo ""
echo "=== CHECK 5: Scope Validation ==="
if [[ ${#SCOPE_PATHS[@]} -gt 0 ]]; then
    scope_violations=""
    for f in $ALL_CHANGED; do
        in_scope=false
        for scope in "${SCOPE_PATHS[@]}"; do
            if [[ "$f" == "$scope"* ]]; then
                in_scope=true
                break
            fi
        done
        if [[ "$in_scope" == "false" ]]; then
            scope_violations+="  OUT OF SCOPE: $f"$'\n'
        fi
    done

    if [[ -n "$scope_violations" ]]; then
        echo "$scope_violations"
        RESULTS[scope]=1
        echo "FAIL: scope validation"
        OVERALL_EXIT=1
    else
        RESULTS[scope]=0
        echo "PASS: scope validation"
    fi
else
    echo "SKIPPED (use --scope <paths> to enable)"
    RESULTS[scope]="SKIP"
fi

# ---------------------------------------------------------------------------
# Human-readable summary
# ---------------------------------------------------------------------------
echo ""
echo "========================================="
echo "          TIER 0 SUMMARY"
echo "========================================="
for check in pytest lint typecheck frontend scope; do
    status="${RESULTS[$check]}"
    if [[ "$status" == "SKIP" ]]; then
        printf "  %-12s SKIPPED\n" "$check"
    elif [[ "$status" == "SKIP_B" ]]; then
        printf "  %-12s SKIP (Mode B)\n" "$check"
    elif [[ "$status" -eq 0 ]]; then
        printf "  %-12s PASS\n" "$check"
    else
        printf "  %-12s FAIL\n" "$check"
    fi
done
echo "========================================="

if [[ ${#MODE_B_CHECKS[@]} -gt 0 ]]; then
    echo "B-MODE ACTIVE: ${MODE_B_CHECKS[*]}"
fi

if [[ $OVERALL_EXIT -eq 0 ]]; then
    echo "TIER 0: ALL CHECKS PASSED"
else
    echo "TIER 0: FAILED"
fi

# ---------------------------------------------------------------------------
# Machine-readable summary (JSON, schema_version 1)
# ---------------------------------------------------------------------------
# Single-line JSON, always emitted (even on FAIL).
# Stable contract for MCP or downstream consumers.

END_EPOCH_MS=$(date +%s%3N 2>/dev/null || echo $(($(date +%s) * 1000)))
DURATION_MS=$((END_EPOCH_MS - START_EPOCH_MS))

json_checks=""
for check in pytest lint typecheck frontend scope; do
    status="${RESULTS[$check]}"
    if [[ "$status" == "SKIP" ]]; then
        label="SKIP"
    elif [[ "$status" == "SKIP_B" ]]; then
        label="SKIP_B"
    elif [[ "$status" -eq 0 ]]; then
        label="PASS"
    else
        label="FAIL"
    fi
    [[ -n "$json_checks" ]] && json_checks+=","
    json_checks+="\"${check}\":\"${label}\""
done

# Mode B array
json_mode_b=""
for mb in "${MODE_B_CHECKS[@]+"${MODE_B_CHECKS[@]}"}"; do
    [[ -n "$json_mode_b" ]] && json_mode_b+=","
    json_mode_b+="\"${mb}\""
done

# Changed files array
json_files=""
for f in $ALL_CHANGED; do
    [[ -n "$json_files" ]] && json_files+=","
    json_files+="\"${f}\""
done

overall_label="PASS"
[[ $OVERALL_EXIT -ne 0 ]] && overall_label="FAIL"

echo ""
echo "--- TIER0_JSON ---"
echo "{\"schema_version\":1,\"overall\":\"${overall_label}\",\"exit_code\":${OVERALL_EXIT},\"started_at\":\"${STARTED_AT}\",\"duration_ms\":${DURATION_MS},\"checks\":{${json_checks}},\"mode_b\":[${json_mode_b}],\"changed_files\":[${json_files}]}"

exit $OVERALL_EXIT
