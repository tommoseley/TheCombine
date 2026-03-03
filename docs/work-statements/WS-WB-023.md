# WS-WB-023: Add Dedicated Task Prompt — propose_work_statements 1.0.0

**Parent:** WP-WB-002
**Dependencies:** None (but consumed by WS-WB-025 via WS-WB-022)

## Deliverables

- `combine-config/prompts/tasks/propose_work_statements/releases/1.0.0/task.prompt.txt`
- `combine-config/prompts/tasks/propose_work_statements/releases/1.0.0/meta.yaml`
- Active release registration as needed

## Requirements

- Inputs explicitly limited: WP + TA (and only declared optional context)
- Output shape: list of WS JSON objects conforming to work_statement schema
- Must produce DRAFT-ready artifacts (no stabilization language, no execution claims)
- Must not emit WP fields or mutate ws_index (the caller handles persistence + ws_index update)
- No ambiguity: this is the only prompt used by the propose station

## Acceptance

- Task resolves through the task execution primitive (WS-WB-022)
- Schema validation passes for typical outputs in test harness

## Allowed Paths

- `combine-config/prompts/tasks/propose_work_statements/`
- `combine-config/_active/active_releases.json` (only if required by prompt registry)

## Prohibited

- Do not reuse or modify the existing `work_statement` task prompt
- Do not add routing logic to the prompt (the caller selects this prompt explicitly)
