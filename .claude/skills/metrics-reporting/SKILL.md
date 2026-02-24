---
name: metrics-reporting
description: Report WS execution metrics at phase boundaries. Use when starting a WS, completing phases, fixing bugs, or closing WS execution to report duration, tests, and costs.
---

# Metrics Reporting

The factory measures its own production line. Claude Code MUST report execution metrics at phase boundaries during WS execution.

## What to Report

**At WS start:**
- WS ID, start timestamp, parent WP ID

**At each phase boundary (tests written / implement / verify):**
- Phase name, duration, pass/fail
- Tests written count (for test phases)
- Files modified count (for implement phases)

**At WS completion:**
- Total duration (wall clock)
- Tests written, tests passing
- Bugs found and fixed autonomously (with test names)
- Files created / modified / deleted
- Rework cycles (how many times verification bounced back to implementation)
- LLM calls made, tokens consumed (input/output)

**On autonomous bug fix:**
- Bug description (one line)
- Root cause (one line)
- Test name
- Fix summary

## How to Report

POST metrics to the developer metrics endpoints when available:

```
POST /api/v1/metrics/ws-execution
POST /api/v1/metrics/bug-fix
```

If endpoints are not yet available, append metrics to the session log in a structured format:

```
## Execution Metrics - WS-DCW-001
- Duration: 23m 14s
- Tests written: 8
- Tests passing: 8/8
- Bugs fixed: 1 (empty initial_context in project_orchestrator)
- Files modified: 3
- Rework cycles: 0
- LLM calls: 12
- Tokens: 45,200 in / 18,400 out
```

## Why This Matters

These metrics feed:
- Quality dashboards for the operator
- Cost analysis per document type
- Continuous improvement (which WSs take longest, which have most rework)
- Customer-facing evidence that the factory works
