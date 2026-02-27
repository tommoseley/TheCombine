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
#   ops/scripts/tier0.sh --ws --scope ops/ tests/      # WS mode: scope mandatory
#   ops/scripts/tier0.sh --skip-checks pytest,lint      # skip expensive checks (harness tests)
#
# WS mode (WS-TIER0-SCOPE-001):
#   Activated by --ws flag or COMBINE_WS_ID env var.
#   When WS mode is active, --scope is MANDATORY (hard fail without it).
#   Scope result is always PASS or FAIL (never SKIPPED) in WS mode.
#
# Checks:
#   1. Backend tests  (pytest)
#   2. Backend lint   (ruff)   — changed/new files only
#   3. Backend types  (mypy)   — FAILS if missing, unless --allow-missing typecheck
#   4. Frontend build (vite)   — auto-runs when spa/ files changed, or --frontend
#   5. Scope validation        — mandatory in WS mode, opt-in otherwise
#   6. Registry integrity      — all active_releases assets resolve (WS-REGISTRY-001)
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
WS_FLAG=false
SCOPE_PATHS=()
ALLOWED_MISSING=()
SKIP_CHECKS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --frontend)
            FRONTEND_FORCED=true
            shift
            ;;
        --ws)
            WS_FLAG=true
            shift
            ;;
        --scope)
            shift
            while [[ $# -gt 0 && ! "$1" =~ ^-- ]]; do
                SCOPE_PATHS+=("$1")
                shift
            done
            ;;
        --skip-checks)
            shift
            if [[ $# -eq 0 ]]; then
                echo "ERROR: --skip-checks requires comma-separated check names" >&2
                exit 2
            fi
            IFS=',' read -ra _skips <<< "$1"
            SKIP_CHECKS+=("${_skips[@]}")
            shift
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
            echo "Usage: tier0.sh [--ws] [--frontend] [--scope path1 ...] [--allow-missing check ...] [--skip-checks check1,check2]" >&2
            exit 2
            ;;
    esac
done

# ---------------------------------------------------------------------------
# WS mode detection (WS-TIER0-SCOPE-001)
# ---------------------------------------------------------------------------
# WS mode is active if --ws flag is set OR COMBINE_WS_ID env var is set.
WS_MODE=false
if [[ "$WS_FLAG" == "true" ]]; then
    WS_MODE=true
elif [[ -n "${COMBINE_WS_ID:-}" ]]; then
    WS_MODE=true
fi

# In WS mode, --scope is mandatory (hard fail).
# Exception: CI with ALLOW_SCOPE_SKIP_IN_CI=1 bypasses this requirement.
if [[ "$WS_MODE" == "true" && ${#SCOPE_PATHS[@]} -eq 0 ]]; then
    if [[ "${CI:-}" == "true" && "${ALLOW_SCOPE_SKIP_IN_CI:-}" == "1" ]]; then
        echo "WARNING: WS mode scope requirement bypassed via ALLOW_SCOPE_SKIP_IN_CI=1"
    else
        echo "FAIL: WS mode requires --scope." >&2
        echo "When running Tier 0 in WS mode (--ws or COMBINE_WS_ID), you MUST" >&2
        echo "provide --scope with the path prefixes from the Work Statement's" >&2
        echo "allowed_paths[] field." >&2
        echo "" >&2
        echo "Example: ops/scripts/tier0.sh --ws --scope ops/scripts/ tests/infrastructure/" >&2
        exit 1
    fi
fi

# Normalize scope prefixes: ensure consistent trailing / for directory prefixes
# (a prefix without / matches as a string prefix, which is the desired behavior
# for both file and directory paths).

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


# (CI guard for WS mode scope is handled above in the WS mode scope check)

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

is_check_skipped() {
    local check="$1"
    for skipped in "${SKIP_CHECKS[@]+"${SKIP_CHECKS[@]}"}"; do
        if [[ "$skipped" == "$check" ]]; then
            return 0
        fi
    done
    return 1
}

# ---------------------------------------------------------------------------
# Collect changed files (used by lint, frontend detection, scope)
# ---------------------------------------------------------------------------
# Test seam: TIER0_CHANGED_FILES_OVERRIDE overrides changed file detection.
# This is used by harness tests to control which files appear as "changed"
# without depending on real git state. Not for production use.
if [[ -n "${TIER0_CHANGED_FILES_OVERRIDE:-}" ]]; then
    changed_files="$TIER0_CHANGED_FILES_OVERRIDE"
    new_untracked=""
# In CI with a known base branch, diff against merge-base for accurate
# branch-level change detection. Locally, diff against HEAD for uncommitted.
elif [[ "${CI:-}" == "true" ]]; then
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
    # Local dev: uncommitted + staged + committed-since-main + untracked
    # Uncommitted and staged capture work-in-progress.
    # Committed-since-main captures work done on the branch but already committed
    # (e.g., SPA changes committed in a prior WS that still need frontend build).
    changed_files=$(git diff --name-only HEAD 2>/dev/null || true)
    changed_staged=$(git diff --name-only --cached 2>/dev/null || true)
    LOCAL_DIFF_BASE=$(git merge-base origin/main HEAD 2>/dev/null || echo HEAD)
    changed_on_branch=$(git diff --name-only "${LOCAL_DIFF_BASE}"...HEAD 2>/dev/null || true)
    changed_files=$(echo -e "${changed_files}\n${changed_staged}\n${changed_on_branch}" || true)
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
if is_check_skipped "pytest"; then
    echo "SKIPPED (--skip-checks)"
    RESULTS[pytest]="SKIP"
else
    # Ignore harness meta-tests to avoid recursive invocation
    python3 -m pytest tests/ -x -q \
        --ignore=tests/infrastructure/test_tier0_harness.py \
        2>&1
    RESULTS[pytest]=$?

    if [[ ${RESULTS[pytest]} -ne 0 ]]; then
        echo "FAIL: pytest"
        OVERALL_EXIT=1
    else
        echo "PASS: pytest"
    fi
fi

# ---------------------------------------------------------------------------
# Check 2: Backend lint (ruff) — changed/new files only
# ---------------------------------------------------------------------------
echo ""
echo "=== CHECK 2: Backend Lint (ruff) ==="

if is_check_skipped "lint"; then
    echo "SKIPPED (--skip-checks)"
    RESULTS[lint]="SKIP"
elif ! command -v ruff &>/dev/null; then
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
    # "No worse than baseline": lint only changed/new Python files that exist.
    # Deleted files appear in git diff but cannot be linted.
    lint_targets=$(echo "$ALL_CHANGED" \
        | grep '\.py$' \
        | grep -E '^(app|tests)/' \
        | while read -r f; do [[ -f "$f" ]] && echo "$f"; done \
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

if is_check_skipped "typecheck"; then
    echo "SKIPPED (--skip-checks)"
    RESULTS[typecheck]="SKIP"
elif ! command -v mypy &>/dev/null; then
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

if is_check_skipped "frontend"; then
    echo "SKIPPED (--skip-checks)"
    RESULTS[frontend]="SKIP"
elif [[ "$FRONTEND_FORCED" == "true" ]]; then
    RUN_FRONTEND=true
    echo "(forced via --frontend)"
elif [[ -n "$spa_changed" ]]; then
    RUN_FRONTEND=true
    echo "(auto-detected spa/ changes)"
fi

if [[ "${RESULTS[frontend]:-}" != "SKIP" ]]; then
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
fi

# ---------------------------------------------------------------------------
# Check 5: Scope validation (conditional; mandatory in WS mode)
# ---------------------------------------------------------------------------
echo ""
echo "=== CHECK 5: Scope Validation ==="
if [[ "$WS_MODE" == "true" ]]; then
    echo "(WS mode: scope enforcement mandatory)"
fi

if is_check_skipped "scope"; then
    echo "SKIPPED (--skip-checks)"
    RESULTS[scope]="SKIP"
elif [[ ${#SCOPE_PATHS[@]} -gt 0 ]]; then
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
        echo "$scope_violations" >&2
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
# Check 6: Registry integrity (WS-REGISTRY-001)
# ---------------------------------------------------------------------------
echo ""
echo "=== CHECK 6: Registry Integrity ==="

if is_check_skipped "registry"; then
    echo "SKIPPED (--skip-checks)"
    RESULTS[registry]="SKIP"
else
    python3 ops/scripts/check_registry_integrity.py 2>&1
    RESULTS[registry]=$?
    if [[ ${RESULTS[registry]} -ne 0 ]]; then
        echo "FAIL: registry integrity"
        OVERALL_EXIT=1
    else
        echo "PASS: registry integrity"
    fi
fi

# ---------------------------------------------------------------------------
# Human-readable summary
# ---------------------------------------------------------------------------
echo ""
echo "========================================="
echo "          TIER 0 SUMMARY"
echo "========================================="
SKIP_COUNT=0
for check in pytest lint typecheck frontend scope registry; do
    status="${RESULTS[$check]}"
    if [[ "$status" == "SKIP" ]]; then
        printf "  %-12s SKIPPED\n" "$check"
        ((SKIP_COUNT++))
    elif [[ "$status" == "SKIP_B" ]]; then
        printf "  %-12s SKIP (Mode B)\n" "$check"
        ((SKIP_COUNT++))
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

if [[ $OVERALL_EXIT -ne 0 ]]; then
    echo "TIER 0: FAILED"
elif [[ $SKIP_COUNT -gt 0 ]]; then
    echo "TIER 0: PASSED WITH SKIPS ($SKIP_COUNT skipped)"
else
    echo "TIER 0: ALL CHECKS PASSED"
fi

# ---------------------------------------------------------------------------
# Machine-readable summary (JSON, schema_version 1)
# ---------------------------------------------------------------------------
# Single-line JSON, always emitted (even on FAIL).
# Stable contract for MCP or downstream consumers.

END_EPOCH_MS=$(date +%s%3N 2>/dev/null || echo $(($(date +%s) * 1000)))
DURATION_MS=$((END_EPOCH_MS - START_EPOCH_MS))

json_checks=""
for check in pytest lint typecheck frontend scope registry; do
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

if [[ $OVERALL_EXIT -ne 0 ]]; then
    overall_label="FAIL"
elif [[ $SKIP_COUNT -gt 0 ]]; then
    overall_label="PASS_WITH_SKIPS"
else
    overall_label="PASS"
fi

# WS mode fields
if [[ "$WS_MODE" == "true" ]]; then
    json_ws_mode="true"
else
    json_ws_mode="false"
fi

# Declared scope paths array
json_scope_paths=""
for sp in "${SCOPE_PATHS[@]+"${SCOPE_PATHS[@]}"}"; do
    [[ -n "$json_scope_paths" ]] && json_scope_paths+=","
    json_scope_paths+="\"${sp}\""
done

echo ""
echo "--- TIER0_JSON ---"
echo "{\"schema_version\":1,\"overall\":\"${overall_label}\",\"exit_code\":${OVERALL_EXIT},\"started_at\":\"${STARTED_AT}\",\"duration_ms\":${DURATION_MS},\"ws_mode\":${json_ws_mode},\"declared_scope_paths\":[${json_scope_paths}],\"checks\":{${json_checks}},\"mode_b\":[${json_mode_b}],\"changed_files\":[${json_files}]}"

exit $OVERALL_EXIT
