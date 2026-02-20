#!/usr/bin/env bash
# =============================================================================
# WS-AWS-DB-005: Destructive action guard for database operations
#
# Sources this file in any script that performs destructive DB operations
# (DROP, TRUNCATE, downgrade, reset). Provides require_confirmation()
# which enforces CONFIRM_ENV=<target_env> before proceeding.
#
# Usage (in another script):
#   source ops/scripts/db_destructive_guard.sh
#   require_confirmation "dev" "reset all tables"
#
# Environment variables:
#   CONFIRM_ENV  - Must match the target environment name
#   CI           - If "true", destructive actions on dev/test fail unless
#                  ALLOW_DESTRUCTIVE_IN_CI=1
# =============================================================================

# ---------------------------------------------------------------------------
# require_confirmation <target_env> <action_description>
#
# Exits with error if:
#   - CONFIRM_ENV is not set
#   - CONFIRM_ENV does not match target_env
#   - CI=true without ALLOW_DESTRUCTIVE_IN_CI=1
# ---------------------------------------------------------------------------
require_confirmation() {
    local target_env="$1"
    local action_desc="${2:-destructive action}"

    # Block wildcard or "all" confirmations
    if [[ "${CONFIRM_ENV:-}" == "*" || "${CONFIRM_ENV:-}" == "all" ]]; then
        echo "ERROR: CONFIRM_ENV=* and CONFIRM_ENV=all are not permitted." >&2
        echo "You must confirm the specific environment: CONFIRM_ENV=$target_env" >&2
        exit 1
    fi

    # Require CONFIRM_ENV
    if [[ -z "${CONFIRM_ENV:-}" ]]; then
        echo "ERROR: Destructive action requires explicit confirmation." >&2
        echo "" >&2
        echo "  Action: $action_desc" >&2
        echo "  Target: $target_env" >&2
        echo "" >&2
        echo "To proceed, set CONFIRM_ENV=$target_env" >&2
        echo "  Example: CONFIRM_ENV=$target_env $0 $target_env" >&2
        exit 1
    fi

    # Verify CONFIRM_ENV matches target
    if [[ "${CONFIRM_ENV}" != "$target_env" ]]; then
        echo "ERROR: CONFIRM_ENV mismatch." >&2
        echo "  Expected: CONFIRM_ENV=$target_env" >&2
        echo "  Got:      CONFIRM_ENV=${CONFIRM_ENV}" >&2
        echo "  This prevents accidentally running destructive actions on the wrong environment." >&2
        exit 1
    fi

    # CI guard
    if [[ "${CI:-}" == "true" ]]; then
        if [[ "${ALLOW_DESTRUCTIVE_IN_CI:-}" != "1" ]]; then
            echo "ERROR: Destructive actions in CI require ALLOW_DESTRUCTIVE_IN_CI=1" >&2
            echo "  Action: $action_desc" >&2
            echo "  Target: $target_env" >&2
            exit 1
        fi
        echo "WARNING: Destructive action permitted in CI via ALLOW_DESTRUCTIVE_IN_CI=1"
    fi

    echo "Confirmed: $action_desc on $target_env"
}
